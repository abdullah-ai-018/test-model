@echo off
echo Starting AI Drywall Detection and Wall Classification Web Interface...
streamlit run drywall_detection/app.py --server.headless=false --server.port=8501
pause
