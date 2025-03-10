"""
# Description

This module contains methods to calculate deuteration levels from different spectra.


# Index

| | |
| --- | --- |
| `impulse_approx()` | Calculate the deuteration levels from INS spectra with the Impulse Approximation |
| `peaks_mapbi3()`   | Estimates CH$_3$NH$_3$PbI$_3$ deuteration by integrating the INS disrotatory peaks |

---
"""


from copy import deepcopy
import aton.alias as alias
from .classes import Spectra, Material
from .fit import area_under_peak, ratio_areas, plateau
import numpy as np


def impulse_approx(
        ins: Spectra,
        material_H: Material,
        material_D: Material,
        threshold: float=600,
        H_df_index: int=0,
        D_df_index: int=1,
    ) -> tuple:
    """Calculate the deuteration levels from INS spectra
    with the *Impulse Approximation*, see
    [Andreani et al., Advances in Physics 66, 1–73 (2017)](https://www.tandfonline.com/doi/full/10.1080/00018732.2017.1317963).

    Protonated and deuterated materials must be specified
    as `aton.spectra.classes.Material` objects.
    Note that this approximation is very sensitive to the mass sample.
    The threshold controls the start of the plateau (in meV)
    to start considering Deep Inelastic Neutron Scattering (DINS).
    The protonated and deuterated dataframe indexes are specified
    by `H_df_index` and `D_df_index`, respectively.

    In this approximation, the ideal ratio between
    the cross-sections and the experimental ratio between
    the pleteaus at high energies should be the same:
    $$
    \\frac{\\text{plateau_D}}{\\text{plateau_H}} \\approx \\frac{\\text{cross_section_D}}{\\text{cross_section_H}}
    $$
    Taking this into account, the deuteration is estimated as:
    $$
    \\text{Deuteration} = \\frac{1-\\text{real_ratio}}{1-\\text{ideal_ratio}}
    $$
    """
    ins = deepcopy(ins)
    material_H = deepcopy(material_H)
    material_D = deepcopy(material_D)
    material_H_grams = 1.0 if material_H.grams is None else material_H.grams
    material_H.grams = material_H_grams
    material_H.set()
    material_D_grams = 1.0 if material_D.grams is None else material_D.grams
    material_D.grams = material_D_grams
    material_D.set()

    material_H.print()
    material_D.print()

    # Make sure units are in meV
    units_in = ins.units
    if units_in not in alias.units['meV']:
        ins.set_units('meV', units_in)

    # Divide the y values of the dataframes by the mols of the material.
    ins.dfs[H_df_index][ins.dfs[H_df_index].columns[1]] = ins.dfs[H_df_index][ins.dfs[H_df_index].columns[1]]
    ins.dfs[D_df_index][ins.dfs[D_df_index].columns[1]] = ins.dfs[D_df_index][ins.dfs[D_df_index].columns[1]]

    plateau_H, plateau_H_error = plateau(ins, [threshold, None], H_df_index)
    plateau_D, plateau_D_error = plateau(ins, [threshold, None], D_df_index)

    plateau_H_normalized = plateau_H / material_H.mols
    plateau_H_normalized_error = plateau_H_normalized * np.sqrt((plateau_H_error / plateau_H)**2 + (material_H.mols_error / material_H.mols)**2)
    plateau_D_normalized = plateau_D / material_D.mols
    plateau_D_normalized_error = plateau_D_normalized * np.sqrt((plateau_D_error / plateau_D)**2 + (material_D.mols_error / material_D.mols)**2)

    # ratio if fully protonated = 1.0
    ratio = plateau_D_normalized / plateau_H_normalized  # ratio_ideal < ratio < 1.0
    ratio_ideal = material_D.cross_section / material_H.cross_section  # 0.0 < ratio_ideal < 1.0

    ratio_error = abs(ratio * np.sqrt((plateau_H_normalized_error / plateau_H_normalized)**2 + (plateau_D_normalized_error / plateau_D_normalized)**2))

    deuteration = (1 - ratio) / (1 - ratio_ideal)
    deuteration_error = abs(deuteration * np.sqrt((ratio_error / ratio)**2))

    print(f'Normalized plateau H:      {plateau_H_normalized} +- {plateau_H_normalized_error}')
    print(f'Normalized plateau D:      {plateau_D_normalized} +- {plateau_D_normalized_error}')
    print(f'Ratio D/H plateaus:        {ratio} +- {ratio_error}')
    print(f'Ratio D/H cross sections:  {ratio_ideal}')

    print(f"\nDeuteration: {deuteration:.2f} +- {deuteration_error:.2f}\n")
    return round(deuteration,2), round(deuteration_error,2)


def peaks_mapbi3(
        ins:Spectra,
        peaks:dict,
        df_index:int=0,
    ) -> str:
    """Estimates CH$_3$NH$_3$PbI$_3$ deuteration by integrating the INS disrotatory peaks.

    The INS disrotatory peaks of CH3NH3 appear at ~38 meV for the fully protonated sample.
    Note that `peaks` must be a dictionary with the peak limits
    and the baseline, as in the example below:
    ```python
    peaks = {
        'baseline' : None,
        'baseline_error' : None,
        'h6d0' : [41, 43],
        'h5d1' : [41, 43],
        'h4d2' : [41, 43],
        'h3d3' : [34.7, 37.3],
        'h2d4' : [31.0, 33.0],
        'h1d5' : [28.0, 30.5],
        'h0d6' : [26.5, 28.0],
        }
    ```
    Peak keywords required for selective deuteration (only C or only N):
    `h6d0`, `h5d1`, `h4d2`, `h3d3`.

    Additional peak keywords required for total deuteration:
    `h2d4`, `h1d5`, `h0d6`.

    If some peak is not present in your sample,
    just set the limits to a small baseline plateau.
    """

    peak_data = deepcopy(ins)

    baseline = 0.0
    baseline_error = 0.0
    if 'baseline' in peaks.keys():
        if peaks['baseline'] is not None:
            baseline = peaks['baseline']
    if 'baseline_error' in peaks.keys():
        if peaks['baseline_error'] is not None:
            baseline_error = peaks['baseline_error']

    run_partial = True
    run_total = True

    h6d0_limits = None
    h5d1_limits = None
    h4d2_limits = None
    h3d3_limits = None
    h2d4_limits = None
    h1d5_limits = None
    h0d6_limits = None

    if 'h6d0' in peaks:
        h6d0_limits = peaks['h6d0']
    if 'h5d1' in peaks:
        h5d1_limits = peaks['h5d1']
    if 'h4d2' in peaks:
        h4d2_limits = peaks['h4d2']
    if 'h3d3' in peaks:
        h3d3_limits = peaks['h3d3']
    if 'h2d4' in peaks:
        h2d4_limits = peaks['h2d4']
    if 'h1d5' in peaks:
        h1d5_limits = peaks['h1d5']
    if 'h0d6' in peaks:
        h0d6_limits = peaks['h0d6']

    if h0d6_limits is None or h1d5_limits is None or h2d4_limits is None or h3d3_limits is None:
        run_total = False
    if h6d0_limits is None or h5d1_limits is None or h4d2_limits is None or h3d3_limits is None:
        run_partial = False

    if not run_partial:
        raise ValueError('No peaks to integrate. Remember to assign peak limits as a dictionary with the keys: h6d0, h5d1, h4d2, h3d3, h2d4, h1d5, h0d6.')

    h6d0_area, h6d0_area_error = area_under_peak(peak_data, [h6d0_limits[0], h6d0_limits[1], baseline, baseline_error], df_index, True)
    h5d1_area, h5d1_area_error = area_under_peak(peak_data, [h5d1_limits[0], h5d1_limits[1], baseline, baseline_error], df_index, True)
    h4d2_area, h4d2_area_error = area_under_peak(peak_data, [h4d2_limits[0], h4d2_limits[1], baseline, baseline_error], df_index, True)
    h3d3_area, h3d3_area_error = area_under_peak(peak_data, [h3d3_limits[0], h3d3_limits[1], baseline, baseline_error], df_index, True)
    h6d0_area /= 6
    h5d1_area /= 5
    h4d2_area /= 4
    h3d3_area /= 3
    h6d0_area_error /= 6
    h5d1_area_error /= 5
    h4d2_area_error /= 4
    h3d3_area_error /= 3
    
    if not run_total:
        total_area = h6d0_area + h5d1_area + h4d2_area + h3d3_area
        total_area_error = np.sqrt(h6d0_area_error**2 + h5d1_area_error**2 + h4d2_area_error**2 + h3d3_area_error**2)

        h6d0_ratio, h6d0_error = ratio_areas(h6d0_area, total_area, h6d0_area_error, total_area_error)
        h5d1_ratio, h5d1_error = ratio_areas(h5d1_area, total_area, h5d1_area_error, total_area_error)
        h4d2_ratio, h4d2_error = ratio_areas(h4d2_area, total_area, h4d2_area_error, total_area_error)
        h3d3_ratio, h3d3_error = ratio_areas(h3d3_area, total_area, h3d3_area_error, total_area_error)

        deuteration = 0 * h6d0_ratio + (1/3) * h5d1_ratio + (2/3) * h4d2_ratio + 1 * h3d3_ratio
        protonation = 1 * h6d0_ratio + (2/3) * h5d1_ratio + (1/3) * h4d2_ratio + 0 * h3d3_ratio

        deuteration_error = np.sqrt((1/3 * h5d1_error)**2 + (2/3 * h4d2_error)**2 + (1 * h3d3_error)**2)
        protonation_error = np.sqrt((1 * h6d0_error)**2 + (2/3 * h5d1_error)**2 + (1/3 * h4d2_error)**2)

    if run_total:
        h2d4_area, h2d4_area_error = area_under_peak(peak_data, [h2d4_limits[0], h2d4_limits[1], baseline, baseline_error], df_index, True)
        h1d5_area, h1d5_area_error = area_under_peak(peak_data, [h1d5_limits[0], h1d5_limits[1], baseline, baseline_error], df_index, True)
        h0d6_area, h0d6_area_error = area_under_peak(peak_data, [h0d6_limits[0], h0d6_limits[1], baseline, baseline_error], df_index, True)
        h2d4_area /= 2
        h1d5_area /= 1
        h0d6_area /= 1
        h2d4_area_error /= 2
        h1d5_area_error /= 1
        h0d6_area_error /= 1

        total_area_CDND = h6d0_area + h5d1_area + h4d2_area + h3d3_area + h2d4_area + h1d5_area + h0d6_area
        total_area_error_CDND = np.sqrt(h6d0_area_error**2 + h5d1_area_error**2 + h4d2_area_error**2 + h3d3_area_error**2 + h2d4_area_error**2 + h1d5_area_error**2 + h0d6_area_error**2)

        h6d0_ratio_CDND, h6d0_error_CDND = ratio_areas(h6d0_area, total_area_CDND, h6d0_area_error, total_area_error_CDND)
        h5d1_ratio_CDND, h5d1_error_CDND = ratio_areas(h5d1_area, total_area_CDND, h5d1_area_error, total_area_error_CDND)
        h4d2_ratio_CDND, h4d2_error_CDND = ratio_areas(h4d2_area, total_area_CDND, h4d2_area_error, total_area_error_CDND)
        h3d3_ratio_CDND, h3d3_error_CDND = ratio_areas(h3d3_area, total_area_CDND, h3d3_area_error, total_area_error_CDND)
        h2d4_ratio_CDND, h2d4_error_CDND = ratio_areas(h2d4_area, total_area_CDND, h2d4_area_error, total_area_error_CDND)
        h1d5_ratio_CDND, h1d5_error_CDND = ratio_areas(h1d5_area, total_area_CDND, h1d5_area_error, total_area_error_CDND)
        h0d6_ratio_CDND, h0d6_error_CDND = ratio_areas(h0d6_area, total_area_CDND, h0d6_area_error, total_area_error_CDND)

        deuteration_CDND = 0 * h6d0_ratio_CDND + (1/6) * h5d1_ratio_CDND + (2/6) * h4d2_ratio_CDND + (3/6) * h3d3_ratio_CDND + (4/6) * h2d4_ratio_CDND + (5/6) * h1d5_ratio_CDND + 1 * h0d6_ratio_CDND
        deuteration_CDND_error = np.sqrt((1/6 * h5d1_error_CDND)**2 + (2/6 * h4d2_error_CDND)**2 + (3/6 * h3d3_error_CDND)**2 + (4/6 * h2d4_error_CDND)**2 + (5/6 * h1d5_error_CDND)**2 + (1 * h0d6_error_CDND)**2)

        protonation_CDND = 1 * h6d0_ratio_CDND + (5/6) * h5d1_ratio_CDND + (4/6) * h4d2_ratio_CDND + (3/6) * h3d3_ratio_CDND + (2/6) * h2d4_ratio_CDND + (1/6) * h1d5_ratio_CDND + 0 * h0d6_ratio_CDND
        protonation_CDND_error = np.sqrt((1 * h6d0_error_CDND)**2 + (5/6 * h5d1_error_CDND)**2 + (4/6 * h4d2_error_CDND)**2 + (3/6 * h3d3_error_CDND)**2 + (2/6 * h2d4_error_CDND)**2 + (1/6 * h1d5_error_CDND)**2)

        deuteration_CDND_amine = 0 * h3d3_ratio_CDND + (1/3) * h2d4_ratio_CDND + (2/3) * h1d5_ratio_CDND + 1 * h0d6_ratio_CDND
        deuteration_CDND_amine_error = np.sqrt((1/3 * h2d4_error_CDND)**2 + (2/3 * h1d5_error_CDND)**2 + (1 * h0d6_error_CDND)**2)

        protonation_CDND_amine = 1 * h3d3_ratio_CDND + (2/3) * h2d4_ratio_CDND + (1/3) * h1d5_ratio_CDND + 0 * h0d6_ratio_CDND
        protonation_CDND_amine_error = np.sqrt((1 * h3d3_error_CDND)**2 + (2/3 * h2d4_error_CDND)**2 + (1/3 * h1d5_error_CDND)**2)

    print()
    if hasattr(ins, "plotting") and ins.plotting.legend != None:
        print(f'Sample:  {ins.plotting.legend[df_index]}')
    else:
        print(f'Sample:  {ins.files[df_index]}')
    print(f'Corrected baseline: {round(baseline,2)} +- {round(baseline_error,2)}')
    if not run_total:
        print(f"HHH {h6d0_limits}:  {round(h6d0_ratio,2)}  +-  {round(h6d0_error,2)}")
        print(f"DHH {h5d1_limits}:  {round(h5d1_ratio,2)}  +-  {round(h5d1_error,2)}")
        print(f"DDH {h4d2_limits}:  {round(h4d2_ratio,2)}  +-  {round(h4d2_error,2)}")
        print(f"DDD {h3d3_limits}:  {round(h3d3_ratio,2)}  +-  {round(h3d3_error,2)}")
        print(f"Amine deuteration:  {round(deuteration,2)}  +-  {round(deuteration_error,2)}")
        print(f"Amine protonation:  {round(protonation,2)}  +-  {round(protonation_error,2)}")
        print()
        return f"{deuteration:.2f} +- {deuteration_error:.2f}"
    else:
        print(f"HHH-HHH {h6d0_limits}:  {round(h6d0_ratio_CDND,2)}  +-  {round(h6d0_error_CDND,2)}")
        print(f"DHH-HHH {h5d1_limits}:  {round(h5d1_ratio_CDND,2)}  +-  {round(h5d1_error_CDND,2)}")
        print(f"DDH-HHH {h4d2_limits}:  {round(h4d2_ratio_CDND,2)}  +-  {round(h4d2_error_CDND,2)}")
        print(f"DDD-HHH {h3d3_limits}:  {round(h3d3_ratio_CDND,2)}  +-  {round(h3d3_error_CDND,2)}")
        print(f"DDD-DHH {h2d4_limits}:  {round(h2d4_ratio_CDND,2)}  +-  {round(h2d4_error_CDND,2)}")
        print(f"DDD-DDH {h1d5_limits}:  {round(h1d5_ratio_CDND,2)}  +-  {round(h1d5_error_CDND,2)}")
        print(f"DDD-DDD {h0d6_limits}:  {round(h0d6_ratio_CDND,2)}  +-  {round(h0d6_error_CDND,2)}")
        print(f"Total deuteration:  {round(deuteration_CDND,2)}  +-  {round(deuteration_CDND_error,2)}")
        print(f"Total protonation:  {round(protonation_CDND,2)}  +-  {round(protonation_CDND_error,2)}")
        print(f"Amine deuteration:  {round(deuteration_CDND_amine,2)}  +-  {round(deuteration_CDND_amine_error,2)}")
        print(f"Amine protonation:  {round(protonation_CDND_amine,2)}  +-  {round(protonation_CDND_amine_error,2)}")
        print()
        return f"{deuteration_CDND_amine:.2f} +- {deuteration_CDND_amine_error:.2f} / {deuteration_CDND:.2f} +- {deuteration_CDND_error:.2f}"

