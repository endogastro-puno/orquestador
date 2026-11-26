@echo off
setlocal
cd /d "%~dp0"
title Orquestador documental - Primer arranque

rem Un PYTHONHOME o PYTHONPATH de otra instalacion rompe Python sin avisar.
set PYTHONHOME=
set PYTHONPATH=

where py >nul 2>nul
if errorlevel 1 goto probar_python
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 goto usar_py

:probar_python
where python >nul 2>nul
if errorlevel 1 goto sin_python
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 goto usar_python
goto sin_python

:usar_py
py -3 herramientas\scripts\empezar.py %*
goto fin

:usar_python
python herramientas\scripts\empezar.py %*
goto fin

:sin_python
echo.
echo No encontre Python 3.10 o superior.
echo Pedile al agente: "no tengo Python instalado, instalalo y segui".
echo.
pause
exit /b 1

:fin
echo.
pause
