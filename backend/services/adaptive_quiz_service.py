# backend/services/adaptive_quiz_service.py
# Corrected version with 'await' and added weak topic identification

import uuid
import numpy as np
from datetime import datetime
from typing import List, Optional, Tuple, Dict, DefaultDict
from collections import defaultdict # Import defaultdict

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

# CATSim components
from catsim.initialization import RandomInitializer, Initializer
from catsim.selection import MaxInfoSelector, Selector
from catsim.estimation import NumericalSearchEstimator, Estimator
from catsim.stopping import MaxItemStopper, MinErrorStopper, Stopper

# Project components
from backend.db.models import QuizQuestion, QuizAttemptState, Consent
from backend.schemas.quiz import (
    QuizAnswerInput,
    QuizNextQuestionResponse,
    QuizQuestionForParticipant,
    QuizAttemptStateCreate,
    # QuizAttemptStateUpdate, # Not used directly here currently
)

# --- Configuration for CAT ---
DEFAULT_MAX_ITEMS = 20
DEFAULT_MIN_SE = 0.35
USE_MIN_ERROR_STOPPER = False
# --- Configuration for Weak Topic Identification ---
WEAK_TOPIC_THRESHOLD = 0.5 # Consider a topic weak if accuracy < 50%
MIN_ITEMS_PER_TOPIC = 2 # Minimum items administered for a topic to be considered for weakness

class AdaptiveQuizService:
    """
    Service layer for managing the adaptive quiz logic using CATSim.
    Handles starting quizzes, processing answers, estimating ability,
    selecting next items, determining stopping conditions, and identifying weak topics.
    """

    def __init__(
        self,
        session: AsyncSession,
        initializer: Optional[Initializer] = None,
        selector: Optional[Selector] = None,
        estimator: Optional[Estimator] = None,
        stopper: Optional[Stopper] = None,
    ):
        """
        Initializes the service with database session and CATSim components.
        Uses default CATSim components if none are provided.

        Args:
            session: The async database session.
            initializer: CATSim initializer component.
            selector: CATSim item selector component.
            estimator: CATSim ability estimator component.
            stopper: CATSim stopping rule component.
        """
        self.session = session
        # Initialize CATSim components with defaults
        self.initializer = initializer or RandomInitializer()
        self.selector = selector or MaxInfoSelector()
        self.estimator = estimator or NumericalSearchEstimator()
        if stopper is None:
             self.stopper = MinErrorStopper(DEFAULT_MIN_SE) if USE_MIN_ERROR_STOPPER else MaxItemStopper(DEFAULT_MAX_ITEMS)
        else:
            self.stopper = stopper

        # Internal cache for item bank to avoid repeated DB calls per request
        self._item_bank: Optional[np.ndarray] = None
        self._item_ids: Optional[List[uuid.UUID]] = None
        self._item_id_to_index_map: Optional[Dict[uuid.UUID, int]] = None
        self._item_index_to_details_map: Optional[Dict[int, QuizQuestion]] = None # Cache for item details

    async def _load_item_bank(self, force_reload: bool = False):
        """
        Loads active quiz questions and their IRT parameters from the database
        into memory structures suitable for CATSim. Caches results.

        Args:
            force_reload: If True, forces reloading from the database even if cached.

        Raises:
            ValueError: If no valid questions with IRT parameters are found.
        """
        # Use cached version if available and not forcing reload
        if self._item_bank is not None and not force_reload:
            return

        print("Loading item bank from database...")
        # --- DB CALL: Needs await ---
        statement = select(QuizQuestion)
        result = await self.session.exec(statement) # Corrected: Added await
        questions = result.all()
        # --- End DB Call ---

        if not questions:
            raise ValueError("No quiz questions found in the database.")

        valid_questions = []
        item_bank_list = []
        item_ids_list = []
        item_index_to_details = {}
        item_id_to_index = {} # Renamed for clarity

        # Use enumerate to get index directly
        for index, q in enumerate(questions):
            irt = q.irt_parameters
            # Ensure IRT parameters exist and are valid numbers
            if (irt and isinstance(irt.get('a'), (int, float)) and
                    isinstance(irt.get('b'), (int, float)) and
                    isinstance(irt.get('c'), (int, float))):
                # CATSim 3PL model: [discrimination (a), difficulty (b), guessing (c), slipping (d=1.0)]
                item_params = [float(irt['a']), float(irt['b']), float(irt['c']), 1.0]
                item_bank_list.append(item_params)
                item_ids_list.append(q.question_id)
                item_index_to_details[index] = q # Map current index to question details
                item_id_to_index[q.question_id] = index # Map question ID to current index
                valid_questions.append(q)
            else:
                 print(f"Warning: Question {q.question_id} skipped due to missing/invalid IRT parameters: {irt}")

        if not item_bank_list:
             raise ValueError("No valid quiz questions with IRT parameters found.")

        # Store loaded data in instance variables
        self._item_bank = np.array(item_bank_list)
        self._item_ids = item_ids_list # List of UUIDs in the order they appear in _item_bank
        self._item_id_to_index_map = item_id_to_index # Map: UUID -> index in _item_bank
        self._item_index_to_details_map = item_index_to_details # Map: index in _item_bank -> QuizQuestion object

        print(f"Loaded {len(self._item_ids)} valid items into the item bank.")

    async def _get_question_details_by_index(self, item_index: int) -> Optional[QuizQuestion]:
        """ Helper to get full question details using the cached index map. """
        if self._item_index_to_details_map is None:
            await self._load_item_bank() # Ensure bank is loaded
        # Check again after loading attempt
        if self._item_index_to_details_map is None:
             raise RuntimeError("Item bank details map not loaded.")

        return self._item_index_to_details_map.get(item_index)


    async def _get_attempt_state(self, attempt_id: uuid.UUID) -> Optional[QuizAttemptState]:
        """Helper to fetch the current attempt state by its UUID."""
        # --- DB CALL: Needs await ---
        statement = select(QuizAttemptState).where(QuizAttemptState.attempt_id == attempt_id)
        result = await self.session.exec(statement) # Corrected: Added await
        attempt = result.first()
        # --- End DB Call ---
        return attempt

    async def start_quiz(self, session_uuid: uuid.UUID, quiz_id: Optional[str] = None) -> Tuple[QuizAttemptState, QuizQuestionForParticipant]:
        """
        Initializes a new quiz attempt for a given session.
        Loads item bank, estimates initial ability, selects first item, saves state.

        Args:
            session_uuid: The session identifier.
            quiz_id: Optional identifier for a specific quiz.

        Returns:
            Tuple containing the newly created QuizAttemptState and the first question schema.

        Raises:
            ValueError: If session not found, no valid items, or cannot select first item.
            RuntimeError: If item bank loading fails unexpectedly.
        """
        # Ensure item bank is loaded
        await self._load_item_bank()
        if self._item_bank is None or self._item_ids is None or self._item_id_to_index_map is None:
             raise RuntimeError("Item bank failed to load or is empty.")

        # 1. Check if session exists
        # Use session.get for primary key lookup (more efficient)
        consent_check = await self.session.get(Consent, session_uuid) # Corrected: Uses session.get
        if not consent_check:
             raise ValueError(f"Cannot start quiz: Session with UUID {session_uuid} not found.")

        # 2. Initialize Ability Estimate
        initial_theta = self.initializer.initialize()

        # 3. Select First Item
        available_indices = np.arange(len(self._item_ids)) # All items available initially
        try:
            first_item_index = self.selector.select(
                items=self._item_bank,
                administered_items=np.array([]), # No items administered yet
                est_theta=initial_theta,
                available_indices=available_indices
            )
        except Exception as e:
            print(f"Error during initial item selection: {e}")
            raise ValueError("Could not select the first item due to selector error.") from e


        if first_item_index is None or first_item_index >= len(self._item_ids):
             raise ValueError("Could not select the first item. Check item bank and selector logic.")

        first_question_id = self._item_ids[first_item_index]

        # 4. Create and Save Initial State
        attempt_data = QuizAttemptStateCreate(quiz_id=quiz_id) # Use schema for default/validation
        new_attempt = QuizAttemptState(
            **attempt_data.model_dump(exclude_unset=True), # Populate from schema defaults
            session_uuid=session_uuid,
            start_time=datetime.utcnow(),
            last_update_time=datetime.utcnow(),
            current_theta=float(initial_theta), # Ensure float
            current_se=None, # SE typically calculated after first response
            administered_items=[], # Store list of UUIDs as strings
            responses=[], # Store list of 0/1 integers
            is_complete=False
        )
        self.session.add(new_attempt)
        await self.session.flush() # Persist to DB to get attempt_id assigned
        await self.session.refresh(new_attempt) # Load the assigned attempt_id

        print(f"Created new quiz attempt {new_attempt.attempt_id} with initial theta {initial_theta:.3f}")

        # 5. Get First Question Details for Participant
        first_question_db = await self._get_question_details_by_index(first_item_index)
        if not first_question_db:
            # This should ideally not happen if item_ids and details map are consistent
            raise RuntimeError(f"Internal Error: Selected first question ID {first_question_id} not found in details map.")

        # Use Pydantic model for validation and field selection
        first_question_participant = QuizQuestionForParticipant.model_validate(first_question_db)

        return new_attempt, first_question_participant

    async def process_answer(self, attempt_id: uuid.UUID, answer_input: QuizAnswerInput) -> QuizNextQuestionResponse:
        """
        Processes an answer, updates state, estimates ability, checks stopping rule, selects next item.
        Also identifies weak topics upon completion.

        Args:
            attempt_id: The UUID of the quiz attempt being processed.
            answer_input: The schema containing the answered question ID and selected option index.

        Returns:
            Response schema containing the next question or completion status (including weak topics).

        Raises:
            ValueError: If attempt/question not found, or attempt already complete.
            RuntimeError: If item bank/mapping issues occur, or item selection fails.
        """
        # Ensure item bank is loaded
        await self._load_item_bank()
        if self._item_bank is None or self._item_ids is None or self._item_id_to_index_map is None or self._item_index_to_details_map is None:
             raise RuntimeError("Item bank failed to load or is invalid.")

        # 1. Get Current State
        attempt_state = await self._get_attempt_state(attempt_id)
        if not attempt_state:
            raise ValueError(f"Quiz attempt state not found for ID: {attempt_id}")
        if attempt_state.is_complete:
            raise ValueError(f"Quiz attempt {attempt_id} is already complete.")

        # 2. Validate Answer and Update History
        answered_question_id = answer_input.question_id
        selected_option_index = answer_input.selected_option_index

        # Map UUID to index for CATSim operations
        answered_item_index = self._item_id_to_index_map.get(answered_question_id)
        if answered_item_index is None:
             raise ValueError(f"Answered question ID {answered_question_id} not found in the loaded item bank map.")

        answered_question_db = await self._get_question_details_by_index(answered_item_index)
        if not answered_question_db:
             raise RuntimeError(f"Internal Error: Question details for index {answered_item_index} not found.")

        # Check correctness and determine response value (0 or 1)
        is_correct = selected_option_index in answered_question_db.correct_answers
        response_value = 1 if is_correct else 0

        # Prepare data structures for CATSim estimation/selection
        # Convert stored UUID strings back to UUIDs then map to indices
        administered_indices = [self._item_id_to_index_map[uuid.UUID(qid)] for qid in attempt_state.administered_items if uuid.UUID(qid) in self._item_id_to_index_map]
        # Append current answer's index and response value
        new_administered_indices = np.append(administered_indices, answered_item_index).astype(int)
        new_responses = np.append(attempt_state.responses, response_value).astype(int)

        # 3. Estimate Ability (Theta) and Standard Error (SE)
        current_theta = attempt_state.current_theta # Start with previous estimate
        current_se = attempt_state.current_se # Start with previous SE
        try:
             estimated_theta = self.estimator.estimate(items=self._item_bank, administered_items=new_administered_indices, response_vector=new_responses, est_theta=current_theta)
             estimated_se = self.estimator.estimate_standard_error(est_theta=estimated_theta, items=self._item_bank, administered_items=new_administered_indices, response_vector=new_responses)
             current_theta = float(estimated_theta) # Update with new estimate
             current_se = float(estimated_se) # Update with new estimate
             print(f"Attempt {attempt_id}: Item {answered_item_index} answered ({'Correct' if is_correct else 'Incorrect'}). New Theta: {current_theta:.3f}, SE: {current_se:.3f}")
        except Exception as e:
             print(f"Warning: Estimation error for attempt {attempt_id}: {e}. Using previous estimates.")
             # Keep previous theta/SE if estimation fails

        # 4. Check Stopping Criteria
        stop_decision = self.stopper.stop(administered_items=self._item_bank[new_administered_indices], theta=current_theta, est_theta_se=current_se, administered_indices = new_administered_indices)
        print(f"Attempt {attempt_id}: Stop decision = {stop_decision}")

        # 5. Update Attempt State common fields
        # Use the updated list of UUID strings
        attempt_state.administered_items.append(str(answered_question_id))
        attempt_state.responses.append(response_value) # Store 0 or 1
        attempt_state.current_theta = current_theta
        attempt_state.current_se = current_se
        attempt_state.last_update_time = datetime.utcnow()
        attempt_state.is_complete = stop_decision

        # --- Finalize if stopping ---
        if stop_decision:
             # --- Call weak topic identification ---
             weak_topics = await self._identify_weak_topics(new_administered_indices, new_responses)
             attempt_state.identified_weak_topics = weak_topics
             # --- End weak topic identification ---

             # Calculate final score (simple percentage correct)
             final_score = sum(new_responses) / len(new_responses) * 100 if len(new_responses) > 0 else 0.0
             attempt_state.final_score_percent = final_score
             print(f"Attempt {attempt_id}: Quiz completed. Final Score: {final_score:.1f}%, Weak Topics: {weak_topics}")

             self.session.add(attempt_state)
             await self.session.flush() # Save final state

             # Return completion status and results
             return QuizNextQuestionResponse(
                 next_question=None,
                 is_complete=True,
                 current_theta=current_theta,
                 current_se=current_se,
                 final_score_percent=final_score, # Include score
                 identified_weak_topics=weak_topics # Include weak topics
             )

        # --- Select Next Item if not stopping ---
        else:
             # Determine available items (indices not yet administered)
             all_indices = np.arange(len(self._item_ids))
             available_indices = np.setdiff1d(all_indices, new_administered_indices, assume_unique=True)

             if len(available_indices) == 0:
                 # Ran out of items before stopping rule met - force stop
                 print(f"Warning: No more items available for attempt {attempt_id}, stopping quiz.")
                 attempt_state.is_complete = True
                 # Identify weak topics even if stopped due to running out of items
                 weak_topics = await self._identify_weak_topics(new_administered_indices, new_responses)
                 attempt_state.identified_weak_topics = weak_topics
                 final_score = sum(new_responses) / len(new_responses) * 100 if len(new_responses) > 0 else 0.0
                 attempt_state.final_score_percent = final_score

                 self.session.add(attempt_state)
                 await self.session.flush()
                 return QuizNextQuestionResponse(
                    next_question=None, is_complete=True, current_theta=current_theta,
                    current_se=current_se, final_score_percent=final_score,
                    identified_weak_topics=weak_topics
                )

             # Select the next item index using the CATSim selector
             try:
                 next_item_index = self.selector.select(items=self._item_bank, administered_items=new_administered_indices, est_theta=current_theta, available_indices=available_indices)
             except Exception as e:
                  print(f"Error during next item selection for attempt {attempt_id}: {e}. Stopping quiz.")
                  attempt_state.is_complete = True
                  weak_topics = await self._identify_weak_topics(new_administered_indices, new_responses)
                  attempt_state.identified_weak_topics = weak_topics
                  final_score = sum(new_responses) / len(new_responses) * 100 if len(new_responses) > 0 else 0.0
                  attempt_state.final_score_percent = final_score
                  self.session.add(attempt_state)
                  await self.session.flush()
                  return QuizNextQuestionResponse(
                    next_question=None, is_complete=True, current_theta=current_theta,
                    current_se=current_se, final_score_percent=final_score,
                    identified_weak_topics=weak_topics
                  )

             if next_item_index is None or next_item_index >= len(self._item_ids) or next_item_index not in available_indices:
                  print(f"Error: Selector returned invalid index ({next_item_index}) for attempt {attempt_id}, stopping.")
                  attempt_state.is_complete = True
                  weak_topics = await self._identify_weak_topics(new_administered_indices, new_responses)
                  attempt_state.identified_weak_topics = weak_topics
                  final_score = sum(new_responses) / len(new_responses) * 100 if len(new_responses) > 0 else 0.0
                  attempt_state.final_score_percent = final_score
                  self.session.add(attempt_state)
                  await self.session.flush()
                  return QuizNextQuestionResponse(
                    next_question=None, is_complete=True, current_theta=current_theta,
                    current_se=current_se, final_score_percent=final_score,
                    identified_weak_topics=weak_topics
                  )

             # Get details for the next question
             next_question_db = await self._get_question_details_by_index(next_item_index)
             if not next_question_db:
                  raise RuntimeError(f"Internal Error: Selected next question index {next_item_index} has no details!")

             # Prepare response for the frontend
             next_question_participant = QuizQuestionForParticipant.model_validate(next_question_db)

             # Save updated state before returning
             self.session.add(attempt_state)
             await self.session.flush() # Commit happens in get_session wrapper

             # Return the next question
             return QuizNextQuestionResponse(
                 next_question=next_question_participant,
                 is_complete=False
                 # Optionally return current theta/SE during the quiz if needed
                 # current_theta=current_theta,
                 # current_se=current_se
             )

    # --- NEW HELPER METHOD ---
    async def _identify_weak_topics(
        self,
        administered_indices: np.ndarray,
        responses: np.ndarray
    ) -> List[str]:
        """
        Identifies topics where the participant performed below a threshold,
        based on the topic tags associated with the administered questions.

        Args:
            administered_indices: Numpy array of integer indices of the items administered.
            responses: Numpy array of 0/1 responses corresponding to administered_indices.

        Returns:
            A list of topic tag strings identified as weak.
        """
        # Ensure item details map is loaded (should be by process_answer)
        if self._item_index_to_details_map is None:
            print("Warning: Cannot identify weak topics, item details map not loaded.")
            return [] # Cannot proceed without item details

        # Use defaultdict to easily track counts per topic
        # Structure: {'topic_tag': {'correct': count, 'total': count}}
        topic_stats: DefaultDict[str, Dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})

        # Iterate through administered items and responses
        for i, item_index in enumerate(administered_indices):
            # Retrieve cached question details using the item's index
            item_details = self._item_index_to_details_map.get(item_index)

            # Check if details and tags exist for this item
            if item_details and item_details.topic_tags:
                is_correct = responses[i] == 1 # Check if the response was correct (1)
                # Iterate through potentially multiple tags per question
                for tag in item_details.topic_tags:
                    if tag: # Ensure tag is not empty or None
                        topic_stats[tag]["total"] += 1 # Increment total count for this tag
                        if is_correct:
                            topic_stats[tag]["correct"] += 1 # Increment correct count if answered correctly

        # Determine weak topics based on threshold and minimum items administered per topic
        weak_topics: List[str] = []
        print("DEBUG: Topic Stats for Weak Topic Identification:", dict(topic_stats)) # Log calculated stats

        for topic, stats in topic_stats.items():
            # Only consider topics where a minimum number of items were seen
            if stats["total"] >= MIN_ITEMS_PER_TOPIC:
                # Calculate accuracy for the topic
                accuracy = stats["correct"] / stats["total"]
                # If accuracy is below the defined threshold, mark as weak
                if accuracy < WEAK_TOPIC_THRESHOLD:
                    weak_topics.append(topic)
                    print(f"DEBUG: Identified weak topic '{topic}' (Accuracy: {accuracy:.2f}, Count: {stats['total']})")

        return weak_topics