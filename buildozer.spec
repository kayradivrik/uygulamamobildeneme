[app]

# (str) Title of your application
title = Choppa YKS

# (str) Package name
package.name = choppayks

# (str) Package domain (needed for android packaging)
package.domain = org.yks

# (str) Source code directory
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,db

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy==2.3.0,kivymd==1.2.0,plyer

# (str) Supported orientations
# Valid values are: landscape, portrait, portrait-upside-down, all
orientation = all

# (list) Permissions
android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE

# (str) OSX Python version
osx.python_version = 3

# =============================================================================
# Android Specific Configurations (Default values to ensure successful build)
# =============================================================================

# (bool) Use --private data directory (True) or public (False)
android.private_storage = True

# (int) Android API to use
android.api = 33

# (int) Minimum API your APK will support.
android.minapi = 21

# (str) Android NDK version to use
android.ndk = 25b

# (bool) Skip byte compile for .py files
android.skip_byte_compile = False

# (str) Format used to package the app for release (aab or apk)
android.release_artifact = apk

# (str) Format used to package the app for debug (apk)
android.debug_artifact = apk
