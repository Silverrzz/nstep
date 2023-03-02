cd C:/nstep/
del nstep.exe
py -m PyInstaller nstep.py --onefile
cd C:/nstep/
rmdir /s /q build
del nstep.spec
copy dist/nstep.exe
rmdir /s /q dist
set "PATH=%PATH%;%cd%"