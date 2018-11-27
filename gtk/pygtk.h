/* -*- Mode: C; c-basic-offset: 4 -*- */
#ifndef _PYGTK_H_
#define _PYGTK_H_

#define NO_IMPORT_PYGOBJECT
#include <pygobject.h>
#include <Python.h>
#include <gtk/gtk.h>

struct _PyGtk_FunctionStruct {
    char *pygtkVersion;

    PyTypeObject *gdkAtom_type;
    PyObject *(* gdkAtom_new)(GdkAtom atom);
    gboolean  (* rectangle_from_pyobject)(PyObject     *object,
					  GdkRectangle *rectangle);
    PyObject    * (*tree_path_to_pyobject) (GtkTreePath *path);
    GtkTreePath * (*tree_path_from_pyobject) (PyObject *object);
};

/* structure definitions for the various object types in PyGTK */
typedef struct {
    PyObject_HEAD
    gchar *name;
    GdkAtom atom;
} PyGdkAtom_Object;

/* routines to get the C object value out of the PyObject wrapper */
#define PyGdkAtom_Get(v) (((PyGdkAtom_Object *)(v))->atom)

/* this section is dependent on whether we are being included from gtkmodule.c
 * or not.  A similar source level interface should be provided in both
 * instances. */
#ifndef _INSIDE_PYGTK_

/* for multi file extensions, define one of these in all but the main file
 * of the module */
#if defined(NO_IMPORT) || defined(NO_IMPORT_PYGTK)
extern struct _PyGtk_FunctionStruct *_PyGtk_API;
#else
struct _PyGtk_FunctionStruct *_PyGtk_API;
#endif

/* type objects */
#define PyGdkAtom_Type          *(_PyGtk_API->gdkAtom_type)

/* type checking routines */
#define PyGdkAtom_Check(v) ((v)->ob_type == _PyGtk_API->gdkAtom_type)

/* type objects */
#define PyGdkAtom_New          (_PyGtk_API->gdkAtom_new)

/* some variables */
#define PYGTK_VERSION (_PyGtk_API->pygtkVersion)

/* public functions */
#define pygdk_rectangle_from_pyobject (_PyGtk_API->rectangle_from_pyobject)
#define pygtk_tree_path_to_pyobject (_PyGtk_API->tree_path_to_pyobject)
#define pygtk_tree_path_from_pyobject (_PyGtk_API->tree_path_from_pyobject)


/* a function to initialise the pygtk functions */

/* Python 2.7 introduced the PyCapsule API and deprecated the CObject API */
#if PY_VERSION_HEX >= 0x03000000
#define init_pygtk() G_STMT_START { \
    void *capsule = PyCapsule_Import("gtk._gtk._PyGtk_API", 0); \
    if (!capsule) { \
        return NULL; \
    } \
    _PyGtk_API = (struct _PyGtk_FunctionStruct*)capsule; \
} G_STMT_END
#elif PY_VERSION_HEX >= 0x02070000
#define init_pygtk() G_STMT_START { \
    void *capsule = PyCapsule_Import("gtk._gtk._PyGtk_API", 0); \
    if (!capsule) { \
        return; \
    } \
    _PyGtk_API = (struct _PyGtk_FunctionStruct*)capsule; \
} G_STMT_END
#else /* PY_VERSION_HEX */
/* Python 2.6 and earlier use the CObject API */
#define init_pygtk() G_STMT_START { \
    PyObject *pygtk = PyImport_ImportModule("gtk"); \
    if (pygtk != NULL) { \
	PyObject *module_dict = PyModule_GetDict(pygtk); \
	PyObject *cobject = PyDict_GetItemString(module_dict, "_PyGtk_API"); \
	if (PyCObject_Check(cobject)) \
	    _PyGtk_API = (struct _PyGtk_FunctionStruct*) \
		PyCObject_AsVoidPtr(cobject); \
	else { \
            PyErr_SetString(PyExc_RuntimeError, \
                            "could not find _PyGtk_API object"); \
	    return; \
        } \
    } else { \
        PyErr_SetString(PyExc_ImportError, \
                        "could not import gtk"); \
        return; \
    } \
} G_STMT_END
#endif /* PY_VERSION_HEX */

#endif

#endif /* !_PYGTK_H_ */
