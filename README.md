# Make sure conda env is active
conda activate ai_tutor_env
# Run server
uvicorn backend.main:app --reload --port 8000

Hard Refresh http://127.0.0.1:8000/app1_survey.html

To Delete Database
rm -f ./data/session.db

To Delete Paper Index
rm -rf ./data/vector_stores/Paper1_faiss_index
