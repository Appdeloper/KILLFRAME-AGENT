@echo off
cd "C:\Users\iamwe\Documents\KILLFRAME AGENT"
git add .
git commit -m "Auto save: %date% %time%"
git push origin main
echo Saved to GitHub!
pause
