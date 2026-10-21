@echo off
setlocal
set "dsbca_args=%*"
set "dsbca_args=%dsbca_args:--DartDefines=-dDartDefines%"
call "%DSBCA_REAL_FLUTTER%" %dsbca_args%
exit /b %ERRORLEVEL%
