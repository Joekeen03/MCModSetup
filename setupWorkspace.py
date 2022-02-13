import subprocess, os, os.path, sys, shutil, re
from collections import namedtuple

AUTHOR_FILE = "authorData.txt"

BASE_REPO = r"https://github.com/SinTh0r4s/ExampleMod1.7.10"
DELETE_DIRS = (".git", ".github")
COM_DIR = r"src\main\java\com"
JAVA_EXT = ".java"
COMMON_PROXY_FILE = "CommonProxy.java"
GRADLE_PROPS_FILE = "gradle.properties"

DEFAULT_AUTHOR = "myname"
DEFAULT_ID = "mymodid"
DEFAULT_MOD_CLASS = "MyMod"
DEFAULT_PACKAGE = f"com.{DEFAULT_AUTHOR}.{DEFAULT_ID}"

INVALID_AUTHOR_MSG = f"Author name is not valid! It should only contain spaces, letters (lower- and upper-case),\
and numbers, and the first character should be a letter."

ModifyStatus = namedtuple("ModifyStatus", "success, data, errors")

# Takes a directory, the name of a file in that directory to modify, and a lambda which takes the file's data,
# and returns a ModifyStatus containing whether the modification was successful, the modified data if it was,
# or the error(s) encountered if it wasn't.
def ModifyFile(fileDir, fileName, modification):
    filePath = os.path.join(fileDir, fileName)
    tempPath = filePath+".temp"
    if not os.path.isfile(filePath):
        print(f"[ERROR] Attempted to modify a file that doesn't exist!\nFile path: {filePath}")
        return
    if os.path.exists(tempPath):
        print(f"[ERROR] Attempting to modify a file, but the temp file for it exists!\n\
File path: {filePath}\nTemp file path: {tempPath}")
        return
    shutil.copyfile(filePath, tempPath) # Backup the file in case we're interrupted while reading/writing
    with open(filePath, 'r') as srcFile:
        data = srcFile.read()
    result = modification(data)
    if result.success:
        with open(filePath, 'w') as tgtFile:
            tgtFile.write(result.data)
    else:
        print(f"[ERROR] Errors were encountered while modifying a file. The file has not been modified.\n\
File path: {filePath}\nErrors: {result.errors}")
        print(result.data)
    os.remove(tempPath)

# Attempts to replace 'expected' occurences of 'oldText' in the 'data' with 'newText', returning a successful
# ModifyStatus if that is successful. If any number of occurences is found other than 'expected', it fails,
# returning a failed ModifyStatus
def CheckReplace(data, oldText, newText, expected=1):
    nOccurences = data.count(oldText)
    if nOccurences != expected:
        error = f"Expected {expected} occurences of '{oldText}', found {nOccurences} instead."
        return ModifyStatus(False, data, (error,))
    else:
        return ModifyStatus(True, data.replace(oldText, newText), None)

# Attempts to chain a series of replacements, as done by CheckReplace. Expects the original text to modify,
# a dictionary containing the replacements as old:(new, expected) key-value pairs.
# Aborts and returns a failed ModifyStatus if any of the CheckReplace's fail; otherwise, returns the final
# CheckReplace's result
def ChainReplace(data, replacements):
    currData = data
    result = None
    for oldText, (newText, expected) in replacements.items():
        result = CheckReplace(currData, oldText, newText, expected=expected)
        if not result.success:
            return ModifyStatus(False, data, result.errors)
        currData = result.data
    # Successful chain
    return result

def ValidateAuthorName(authorName):
    return authorName.replace(' ', '').isalnum() and authorName[0].isalpha()

def LoadAuthorFile():
    if not os.path.isfile(AUTHOR_FILE):
        print(f"No author file found. Author filename: {AUTHOR_FILE}")
        return
    
    with open(AUTHOR_FILE, 'r') as authorFile:
        lines = authorFile.read().splitlines()
    if len(lines) != 2:
        print("Author data file is not valid! It should have exactly two lines, the first one holding the\
author's username, the second one holding the master path for the mod folders.")
        return

    authorName, modFolder = lines
    if not ValidateAuthorName(authorName):
        print(f"{INVALID_AUTHOR_MSG}\nAuthor name in author data file: {authorName}")
        return
    if not os.path.isdir(modFolder):
        print(f"Master mod directory does not exist, or is not a folder!\nFolder in author data file: {modFolder}")
        return

    return authorName, modFolder

def GetAuthorInfo():
    authorData = LoadAuthorFile()
    if authorData:
        return authorData
    else:
        print("Could not load author data!")
    
    authorName = input("Please enter your author name (or leave blank to abort): ")
    if len(authorName) == 0:
        print("Author name left blank. Quitting...")
        sys.exit(-1)
    if not ValidateAuthorName(authorName):
        print(f"{INVALID_AUTHOR_MSG}\nAuthor name received: {authorName}")
        sys.exit(-1)
    
    masterPath = input("Please enter the main directory the mod folders should be created under\
(or leave blank to abort):\n>")
    if len(masterPath) == 0:
        print("Master mod path left blank. Quitting...")
        sys.exit(-1)
    if not os.path.isdir(masterPath):
        print(f"Master mod directory does not exist, or is not a folder!\
\nPath received: {masterPath}")
        return
    return authorName, masterPath

def Main():
    authorName, masterPath = GetAuthorInfo()
    modName = input("Please enter the mod's name (or leave blank to abort): ")
    if len(modName) == 0:
        print("Mod name left blank. Quitting...")
        sys.exit(-1)
    
    modPath = os.path.join(masterPath, modName)
    if os.path.exists(modPath):
        print(f"[FATAL] A mod with that name already exists at: {modPath}")
        sys.exit(-1)
    print(f"Setting up git repo for mod: {modName}")
    #modID = input("Please enter the mod's ID: ")
    # Dynamically generate the modID and mod class name from the mod name
    modClassName = modName.replace(' ', '')
    modID = modClassName.lower()
    modClassFile = f"{modClassName}.java"
    modPackage = f"com.{authorName}.{modID}"
    subprocess.call(["git", "clone", BASE_REPO, modPath])
    for delDir in DELETE_DIRS:
        subprocess.call(["cmd", "/c", "rmdir", "/s", "/q", '{}'.format(os.path.join(modPath, delDir))])

    comPath = os.path.join(modPath, COM_DIR)
    authorPath = os.path.join(comPath, authorName)
    modJavaPath = os.path.join(authorPath, modID)
    os.rename(os.path.join(comPath, DEFAULT_AUTHOR), authorPath)
    os.rename(os.path.join(authorPath, DEFAULT_ID), modJavaPath)
    os.rename(os.path.join(modJavaPath, DEFAULT_MOD_CLASS+".java"), os.path.join(modJavaPath, modClassFile))

    # Modify the package names
    packageLine = f"package {modPackage};"
    def ReplacePackage(fileData):
        return CheckReplace(fileData, f"package {DEFAULT_PACKAGE};", packageLine)
    
    for fileName in os.listdir(modJavaPath):
        if fileName[-len(JAVA_EXT):] == JAVA_EXT:
            ModifyFile(modJavaPath, fileName, ReplacePackage)

    # Modify a couple lines in CommonProxy.java to refer to the correct mod name.
    defaultInfoLine = f"{DEFAULT_MOD_CLASS}.info("
    newInfoLine = f"{modClassName}.info("
    ModifyFile(modJavaPath, COMMON_PROXY_FILE, lambda data: CheckReplace(data, defaultInfoLine, newInfoLine,
                                                                         expected=2))

    # Modify the mod class's name inside the actual mod file
    defaultClassLine = f"public class {DEFAULT_MOD_CLASS} {{"
    newClassLine = f"public class {modClassName} {{"
    ModifyFile(modJavaPath, modClassFile, lambda data: CheckReplace(data, defaultClassLine, newClassLine))

    # Modify the gradle.properties
    # Dictionary of replacements - the key is the line to replace, and the value is what it should be replaced with
    replaceLines = {f"modName = {DEFAULT_MOD_CLASS}": (f"modName = {modName}", 1),
                    f"modId = {DEFAULT_ID}": (f"modId = {modID}", 1),
                    f"{DEFAULT_PACKAGE}": (f"{modPackage}", 5)}
    ModifyFile(modPath, GRADLE_PROPS_FILE, lambda data: ChainReplace(data, replaceLines))

    subprocess.call(["git", "init"], cwd=modPath)
    subprocess.call(["git", "add", "*"], cwd=modPath)
    subprocess.call(["git", "commit", "--message", "Initial Commit"], cwd=modPath)
    # TODO - Maybe auto-link to a github repo, too?
    remote = input("Please enter a remote repo to link to (or nothing to not link):\n>")
    if len(remote) > 0:
        print("Linking to remote...")
        subprocess.call(f"git remote add origin {remote}", cwd=modPath)
        subprocess.call("git branch -M main", cwd=modPath)
        subprocess.call("git push -u origin main", cwd=modPath)
    else:
        print("Not linking to remote.")
    print("Setting up gradle...")
    subprocess.call("cmd /c gradlew setupDecompWorkspace", cwd=modPath)
    print("Setup complete.")

if __name__ == "__main__":
    Main()
