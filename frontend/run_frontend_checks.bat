@echo off
cd /d "%~dp0"
call npm.cmd run lint > lint-build.log 2>&1
echo LINT_EXIT=%ERRORLEVEL% >> lint-build.log
call npm.cmd run test >> lint-build.log 2>&1
echo TEST_EXIT=%ERRORLEVEL% >> lint-build.log
call npm.cmd run build >> lint-build.log 2>&1
echo BUILD_EXIT=%ERRORLEVEL% >> lint-build.log
