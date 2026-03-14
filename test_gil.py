import sysconfig

if sysconfig.get_config_var("Py_GIL_DISABLED"):
    print("Free-threading")
else:
    print("Standard CPython")
