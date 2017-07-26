"""

MOL METHODS
====================

Compendium of methods for SMILES parsing and molecular metrics handling.

This module is mainly a reorganization of Gabriel Guimaraes and Benjamin
Sanchez-Lengeling's original implementation (http://github.com/gablg1/ORGAN).

Carlos Outeiral has cleaned up and documented the code, as well
as added a few functions and modified the I/O part. Benjamin Sanchez-Lengeling
has added new mathematical utilities.
"""

from __future__ import absolute_import, division, print_function
import os
import csv
import numpy as np
from rdkit.Chem import AllChem as Chem
from rdkit.Chem import MolFromSmiles, MolToSmiles

""" DATA I/O """


def read_smi(filename):
    """Reads SMILES from a .smi file.

    Arguments
    -----------

        - filename. String pointing to the .smi file.

    """

    with open(filename) as file:
        smiles = file.readlines()
    smiles = [i.strip() for i in smiles]
    return smiles

def read_smiles_csv(filename):
    """Reads SMILES from a .csv file

    Arguments
    -----------

        - filename. String pointing to the .csv file.

    Note
    -----------
        
        This function will assume that the SMILES are
        in column 0.

    """
    with open(filename) as file:
        reader = csv.reader(file)
        smiles_idx = next(reader).index("smiles")
        data = [row[smiles_idx] for row in reader]
    return data

def load_train_data(filename):
    """Loads training data from a .csv or .smi file

    Arguments
    -----------

        - filename. String pointing to the .csv or .smi file.

    """
    ext = filename.split(".")[-1]
    if ext == 'csv':
        return read_smiles_csv(filename)
    if ext == 'smi':
        return read_smi(filename)
    else:
        raise ValueError('data is not smi or csv!')
    return

def save_smi(name, smiles):
    """Saves SMILES data as a .smi file.

    Arguments
    -----------

        - filename. String pointing to the .smi file.

        - smiles. List of SMILES strings to be saved.

    """
    if not os.path.exists('epoch_data'):
        os.makedirs('epoch_data')
    smi_file = os.path.join('epoch_data', "{}.smi".format(name))
    with open(smi_file, 'w') as afile:
        afile.write('\n'.join(smiles))
    return

""" MATHEMATICAL UTILITIES """

def gauss_remap(x, x_mean, x_std):
    """Remaps a given value to a gaussian distribution.

    Arguments
    -----------

        - x. Value to be remapped.

        - x_mean. Mean of the distribution.

        - x_std. Standard deviation of the distribution.

    """

    return np.exp(-(x - x_mean)**2 / (x_std**2))

def remap(x, x_min, x_max):
    """Remaps a given value to [0, 1].

    Arguments
    -----------

        - x. Value to be remapped.

        - x_min. Minimum value (will correspond to 0).

        - x_max. Maximum value (will correspond to 1).

    Note
    -----------

        If x > x_max or x < x_min, the value will be outside
        of the [0, 1] interval. 

    """

    if x_max != 0 and x_min != 0:
        return 0
    elif x_max - x_min == 0:
        return x
    else:
        return (x - x_min) / (x_max - x_min)

def constant_range(x, x_low, x_high):

    if hasattr(x, "__len__"):
        return np.array([constant_range_func(xi, x_low, x_high) for xi in x])
    else:
        return constant_range_func(x, x_low, x_high)

def constant_range_func(x, x_low, x_high):
    """Returns 1 if x is in [x_low, x_high] and 0 if not."""

    if x <= x_low or x >= x_high:
        return 0
    else:
        return 1


def constant_bump_func(x, x_low, x_high, decay=0.025):
    if x <= x_low:
        return np.exp(-(x - x_low)**2 / decay)
    elif x >= x_high:
        return np.exp(-(x - x_high)**2 / decay)
    else:
        return 1


def constant_bump(x, x_low, x_high, decay=0.025):
    if hasattr(x, "__len__"):
        return np.array([constant_bump_func(xi, x_low, x_high, decay) for xi in x])
    else:
        return constant_bump_func(x, x_low, x_high, decay)


def smooth_plateau(x, x_point, decay=0.025, increase=True):
    if hasattr(x, "__len__"):
        return np.array([smooth_plateau_func(xi, x_point, decay, increase) for xi in x])
    else:
        return smooth_plateau_func(x, x_point, decay, increase)


def smooth_plateau_func(x, x_point, decay=0.025, increase=True):
    if increase:
        if x <= x_point:
            return np.exp(-(x - x_point)**2 / decay)
        else:
            return 1
    else:
        if x >= x_point:
            return np.exp(-(x - x_point)**2 / decay)
        else:
            return 1


def pct(a, b):
    if len(b) == 0:
        return 0
    return float(len(a)) / len(b)

"""Encoding/decoding utilities"""

def canon_smile(smile):
    """Transforms to canonic SMILES"""
    return MolToSmiles(MolFromSmiles(smile))

def verified_and_below(smile, max_len):
    """Returns True if the SMILES string is valid and
    its length is less than max_len."""
    return len(smile) < max_len and verify_sequence(smile)

def verify_sequence(smile):
    """Returns True if the SMILES string is valid and
    its length is less than max_len."""
    mol = Chem.MolFromSmiles(smile)
    return smile != '' and mol is not None and mol.GetNumAtoms() > 1

def apply_to_valid(smile, fun, **kwargs):
    """Returns fun(smile, **kwargs) if smiles is a valid
    SMILES string, and 0.0 otherwise."""
    mol = Chem.MolFromSmiles(smile)
    return fun(mol, **kwargs) if smile != '' and mol is not None and mol.GetNumAtoms() > 1 else 0.0

def filter_smiles(smiles):
    """Filters out valid SMILES string from a list."""
    return [smile for smile in smiles if verify_sequence(smile)]

def build_vocab(smiles, pad_char='_', start_char='^'):
    """Builds the vocabulary dictionaries.

    Arguments
    -----------

        - smiles. List of SMILES.

        - pad_char. Char used for padding. '_' by default.

        - start_char. First char of every generated string.
        '^' by default.

    Returns
    -----------
        
        - char_dict. Dictionary which maps a given character
        to a number

        - ord_dict. Dictionary which maps a given number to a
        character.

    """
    i = 1
    char_dict, ord_dict = {start_char: 0}, {0: start_char}
    for smile in smiles:
        for c in smile:
            if c not in char_dict:
                char_dict[c] = i
                ord_dict[i] = c
                i += 1
    char_dict[pad_char], ord_dict[i] = i, pad_char
    return char_dict, ord_dict

def pad(smile, n, pad_char='_'):
    """Adds the padding char (by default '_') to a string
    until it is of n length"""
    if n < len(smile):
        return smile
    return smile + pad_char * (n - len(smile))

def unpad(smile, pad_char='_'): 
    """Removes the padding of a string"""
    return smile.rstrip(pad_char)

def encode(smile, max_len, char_dict): 
    """Encodes a SMILES string using the previously built
    vocabulary."""
    return [char_dict[c] for c in pad(smile, max_len)]

def decode(ords, ord_dict): 
    """Decodes a SMILES string using the previously built
    vocabulary."""
    return unpad(''.join([ord_dict[o] for o in ords]))

def compute_results(model_samples, train_data, ord_dict, results={}, verbose=True):
    samples = [decode(s, ord_dict) for s in model_samples]
    results['mean_length'] = np.mean([len(sample) for sample in samples])
    results['n_samples'] = len(samples)
    results['uniq_samples'] = len(set(samples))
    verified_samples = []
    unverified_samples = []
    for sample in samples:
        if verify_sequence(sample):
            verified_samples.append(sample)
        else:
            unverified_samples.append(sample)
    results['good_samples'] = len(verified_samples)
    results['bad_samples'] = len(unverified_samples)
    # # collect metrics
    # metrics = ['novelty', 'hard_novelty', 'soft_novelty',
    #            'diversity', 'conciseness', 'solubility',
    #            'naturalness', 'synthesizability']

    # for objective in metrics:
    #     func = load_reward(objective)
    #     results[objective] = np.mean(func(verified_samples, train_data))

    # save smiles
    if 'Batch' in results.keys():
        smi_name = '{}_{}'.format(results['exp_name'], results['Batch'])
        save_smi(smi_name, samples)
        results['model_samples'] = smi_name
    # print results
    if verbose:
        # print_results(verified_samples, unverified_samples, metrics, results)
        print_results(verified_samples, unverified_samples, results)
    return

def print_results(verified_samples, unverified_samples, results={}):
    print('~~~ Summary Results ~~~')
    print('{:15s} : {:6d}'.format("Total samples", results['n_samples']))
    percent = results['uniq_samples'] / float(results['n_samples']) * 100
    print('{:15s} : {:6d} ({:2.2f}%)'.format(
        'Unique', results['uniq_samples'], percent))
    percent = results['bad_samples'] / float(results['n_samples']) * 100
    print('{:15s} : {:6d} ({:2.2f}%)'.format('Unverified',
                                             results['bad_samples'], percent))
    percent = results['good_samples'] / float(results['n_samples']) * 100
    print('{:15s} : {:6d} ({:2.2f}%)'.format(
        'Verified', results['good_samples'], percent))
    # print('\tmetrics...')
    # for i in metrics:
    #     print('{:20s} : {:1.4f}'.format(i, results[i]))

    if len(verified_samples) > 10:
        print('\nExample of good samples:')

        for s in verified_samples[0:10]:
            print('' + s)
    else:
        print('\nno good samples found :(')

    if len(unverified_samples) > 10:
        print('\nExample of bad samples:')
        for s in unverified_samples[0:10]:
            print('' + s)
    else:
        print('\nno bad samples found :(')

    print('~~~~~~~~~~~~~~~~~~~~~~~')
    return

