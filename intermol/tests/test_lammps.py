from collections import OrderedDict
from copy import copy
from glob import glob
import os
from pkg_resources import resource_filename

import logging
import numpy as np
from six import string_types
import sys

from intermol import convert
from intermol.tests.testing_tools import (add_handler, remove_handler,
                                          summarize_results, ENGINES,
                                          command_line_flags)

logger = logging.getLogger('InterMolLog')
testing_logger = logging.getLogger('testing')
if not testing_logger.handlers:
    testing_logger.setLevel(logging.DEBUG)
    h = logging.StreamHandler()
    h.setLevel(logging.INFO)  # ignores DEBUG level for now
    f = logging.Formatter("%(levelname)s %(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S")
    h.setFormatter(f)
    testing_logger.addHandler(h)


def test_lammps_unit():
    """Run the LAMMPS unit tests. """
    flags = {'unit': True,
             'energy': True,
             'lammps': True}

    testing_logger.info('Running unit tests')
    output_dir = resource_filename('intermol', 'tests/unit_test_outputs')
    try:
        os.makedirs(output_dir)
    except OSError:
        if not os.path.isdir(output_dir):
            raise
    _run_lammps_and_compare(flags, test_tolerance=1e-4, test_type='unit')


def test_lammps_stress():
    """Run the LAMMPS stress tests. """
    flags = {'stress': True,
             'energy': True,
             'lammps': True}

    testing_logger.info('Running stress tests')
    output_dir = resource_filename('intermol', 'tests/stress_test_outputs')
    try:
        os.makedirs(output_dir)
    except OSError:
        if not os.path.isdir(output_dir):
            raise
    _run_lammps_and_compare(flags, test_tolerance=1e-4, test_type='stress')


def _run_lammps_and_compare(flags, test_tolerance, test_type='unit'):
    results = _convert_from_lammps(flags, test_type=test_type)
    zeros = np.zeros(shape=(len(results['lammps'])))
    for engine, tests in results.items():
        tests = np.array(tests.values())
        try:
            passed = np.allclose(tests, zeros, atol=test_tolerance)
        except TypeError:
            raise Exception('Found non-numeric result for LAMMPS to {0}. This '
                            'probably means an error occured somewhere in the '
                            'conversion.\n\n'.format(engine.upper()))
        if passed:
            print('All {0} tests for LAMMPS to {1} match within {2:.1e} kJ/mol.'.format(test_type, engine.upper(), test_tolerance))
        else:
            raise Exception('{0} tests do not match within {1:.1e} kJ/mol.'.format(test_type, test_tolerance))


def _convert_from_lammps(flags, test_type='unit'):
    """Run all LAMMPS tests of a particular type.

    Args:
        flags (dict): Flags passed to `convert.py`.
        test_type (str, optional): The test suite to run. Defaults to 'unit'.
    Returns:
        results (dict of dicts): The results of all conversions.
            {'gromacs': {'bond1: result, 'bond2: results...},
            'lammps': {'bond1: result, 'bond2: results...},
            ...}

    """
    test_dir = resource_filename('intermol', 'tests/lammps/{0}_tests'.format(test_type))

    input_files = sorted(glob(os.path.join(test_dir, '*/*.input')))
    names = [os.path.splitext(os.path.basename(inp))[0] for inp in input_files]

    # The results of all conversions are stored in nested dictionaries:
    # results = {'gromacs': {'bond1: result, 'bond2: result...},
    #            'lammps': {'bond1: result, 'bond2: result...},
    #            ...}
    per_file_results = OrderedDict((k, None) for k in names)
    results = {engine: copy(per_file_results) for engine in ENGINES}

    base_output_dir = resource_filename('intermol', 'tests/{0}_test_outputs/from_lammps'.format(test_type))
    try:
        os.makedirs(base_output_dir)
    except OSError:
        if not os.path.isdir(base_output_dir):
            raise

    for input_file, name in zip(input_files, names):
        testing_logger.info('Converting {0}'.format(name))
        odir = '{0}/{1}'.format(base_output_dir, name)
        try:
            os.makedirs(odir)
        except OSError:
            if not os.path.isdir(odir):
                raise

        flags['lmp_in'] = input_file
        flags['odir'] = odir
        for engine in ENGINES:
            flags[engine] = True

        h1, h2 = add_handler(odir)
        cmd_line_equivalent = command_line_flags(flags)

        logger.info('Converting {0} with command:\n'.format(input_file))
        logger.info('    python convert.py {0}'.format(
            ' '.join(cmd_line_equivalent)))

        diff = convert.main(flags)
        for engine, result in diff.items():
            results[engine][name] = result
        remove_handler(h1, h2)

    summarize_results('lammps', results, base_output_dir)
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Run the LAMMPS tests.')

    type_of_test = parser.add_argument('-t', '--type', metavar='test_type',
            default='unit', help="The type of tests to run: 'unit' or 'stress'.")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = vars(parser.parse_args())
    if args['type'] == 'unit':
        test_lammps_unit()
    if args['type'] == 'stress':
        test_lammps_stress()














