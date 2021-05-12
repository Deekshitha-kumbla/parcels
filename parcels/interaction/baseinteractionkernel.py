import re
import _ctypes
import inspect
import numpy.ctypeslib as npct
from time import time as ostime
from os import path
from os import remove
from sys import platform
from sys import version_info
from weakref import finalize
from ast import FunctionDef
from hashlib import md5
from parcels.tools.loggers import logger
from numpy import ndarray

try:
    from mpi4py import MPI
except:
    MPI = None

from parcels.tools.global_statics import get_cache_dir

# === import just necessary field classes to perform setup checks === #
from parcels.field import Field
from parcels.field import NestedField
from parcels.field import SummedField
from parcels.grid import GridCode
from parcels.application_kernels import AdvectionRK4_3D
from parcels.application_kernels import AdvectionAnalytical
from parcels.tools.statuscodes import OperationCode
from parcels.kernel.basekernel import BaseKernel

__all__ = ['BaseKernel']


re_indent = re.compile(r"^(\s+)")


class BaseInteractionKernel(BaseKernel):
    """Base super class for Interaction Kernel objects that encapsulates
    auto-generated code.
    """

    def __init__(self, fieldset, ptype, pyfunc=None, funcname=None,
                 funccode=None, py_ast=None, funcvars=None,
                 c_include="", delete_cfiles=True):
        if pyfunc is not None:
            if isinstance(pyfunc, list):
                funcname = ''.join([func.__name__ for func in pyfunc])
            else:
                funcname = pyfunc.__name__

        super(BaseInteractionKernel, self).__init__(
            fieldset=fieldset, ptype=ptype, pyfunc=pyfunc, funcname=funcname,
            funccode=funccode, py_ast=py_ast, funcvars=funcvars,
            c_include=c_include, delete_cfiles=delete_cfiles)

        if pyfunc is not None:
            if isinstance(pyfunc, list):
                self._pyfunc = pyfunc
            else:
                self._pyfunc = [pyfunc]

        # Generate the kernel function and add the outer loop
        if self._ptype.uses_jit:
            raise NotImplementedError("Interaction Kernels do not support"
                                      " JIT mode currently.")

    def __del__(self):
        # Clean-up the in-memory dynamic linked libraries.
        # This is not really necessary, as these programs are not that large, but with the new random
        # naming scheme which is required on Windows OS'es to deal with updates to a Parcels' kernel.)
        # It is particularly unneccessary for Interaction Kernels at this time (as this functionality
        # is as of yet not implemented).
        super().__del__()

    @property
    def ptype(self):
        return self._ptype

    @property
    def pyfunc(self):
        return self._pyfunc

    @property
    def fieldset(self):
        return self._fieldset

    @property
    def c_include(self):
        return self._c_include

    @property
    def _cache_key(self):
        raise NotImplementedError

    @staticmethod
    def fix_indentation(string):
        raise NotImplementedError

    def check_fieldsets_in_kernels(self, pyfunc):
        # Currently, the implemented interaction kernels do not impose
        # any requirements on the fieldset
        pass

    def check_kernel_signature_on_version(self):
        """
        returns numkernelargs
        Adaptation of this method in the BaseKernel that works with
        lists of functions.
        """
        numkernelargs = []
        if self._pyfunc is not None and isinstance(self._pyfunc, list):
            for func in self._pyfunc:
                if version_info[0] < 3:
                    numkernelargs.append(
                        len(inspect.getargspec(func).args)
                    )
                else:
                    numkernelargs.append(
                        len(inspect.getfullargspec(func).args)
                    )
        return numkernelargs

    def remove_lib(self):
        # Currently, no libs are generated/linked, so nothing has to be
        # removed
        pass

    def get_kernel_compile_files(self):
        raise NotImplementedError

    def compile(self, compiler):
        raise NotImplementedError

    def load_lib(self):
        raise NotImplementedError

    def merge(self, kernel, kclass):
        assert self.__class__ == kernel.__class__
        funcname = self.funcname + kernel.funcname
        # delete_cfiles = self.delete_cfiles and kernel.delete_cfiles
        pyfunc = self._pyfunc + kernel._pyfunc
        return kclass(self._fieldset, self._ptype, pyfunc=pyfunc)

    def __add__(self, kernel):
        if not isinstance(kernel, BaseInteractionKernel):
            kernel = BaseInteractionKernel(self.fieldset, self.ptype, pyfunc=kernel)
        return self.merge(kernel, BaseInteractionKernel)

    def __radd__(self, kernel):
        if not isinstance(kernel, BaseInteractionKernel):
            kernel = BaseInteractionKernel(self.fieldset, self.ptype, pyfunc=kernel)
        return kernel.merge(self, BaseInteractionKernel)

    @staticmethod
    def cleanup_remove_files(lib_file, all_files_array, delete_cfiles):
        raise NotImplementedError

    @staticmethod
    def cleanup_unload_lib(lib):
        raise NotImplementedError

    def execute_jit(self, pset, endtime, dt):
        raise NotImplementedError
