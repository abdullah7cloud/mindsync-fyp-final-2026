@echo off
rem Opens backend\.env in Notepad so you can type your mail settings yourself.
rem The password stays on your laptop; never commit this file.
notepad "%~dp0backend\.env"
