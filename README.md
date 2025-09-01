
CLINK C:\Projects\agentic_test>SETLOCAL ENABLEDELAYEDEXPANSION 

CLINK C:\Projects\agentic_test>REM The menuinst v2 json file is not compatible with menuinst versions 

CLINK C:\Projects\agentic_test>REM older than 2.1.1. Copy the appropriate file as the menu file. 

CLINK C:\Projects\agentic_test>SET "LOGFILE=\.messages.txt" 

CLINK C:\Projects\agentic_test>SET "MENU_DIR=\Menu" 

CLINK C:\Projects\agentic_test>SET "MENU_PATH=\Menu\_menu.json" 

CLINK C:\Projects\agentic_test>IF EXIST "" (
SET PYTHON_CMD=""  
 GOTO :get_menuinst 
) 

CLINK C:\Projects\agentic_test>IF EXIST "\_conda.exe" (
SET PYTHON_CMD="\_conda.exe" python  
 GOTO :get_menuinst 
) 

CLINK C:\Projects\agentic_test>IF EXIST "\_conda.exe" (
SET PYTHON_CMD="\_conda.exe" python  
 GOTO :get_menuinst 
) 

CLINK C:\Projects\agentic_test>GOTO :menuinst_too_old 

CLINK C:\Projects\agentic_test>ECHO.  1>>"\.messages.txt" 

CLINK C:\Projects\agentic_test>ECHO This package requires menuinst v2.1.1 in the base environment.  1>>"\.messages.txt" 

CLINK C:\Projects\agentic_test>ECHO Please update menuinst in the base environment and reinstall .  1>>"\.messages.txt" 

CLINK C:\Projects\agentic_test>EXIT /B 1 
