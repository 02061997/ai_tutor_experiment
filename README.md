# Make sure conda env is active
conda activate ai_tutor_env
# Run server
uvicorn backend.main:app --reload --port 8000

Hard Refresh http://127.0.0.1:8000/app1_survey.html
