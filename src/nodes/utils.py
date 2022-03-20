# note: the doctsring code below within
# """ is converted to a restructuredText
# .rst file by sphinx to automatically
# generate the api's documentation
#
# docstring style used: Google style
"""
    module

    Copyright 2022 by Steeve Laquitaine, GNU license 
"""

from collections import defaultdict
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from numpy import arctan2, cos, sin
from scipy.optimize import fmin
from src.nodes.data import VonMises
from src.nodes.util import (
    get_circ_conv,
    get_deg_to_rad,
    get_rad_to_deg,
    is_empty,
)

pd.options.mode.chained_assignment = None


def fit_maxlogl(
    database: pd.DataFrame,
    prior_shape: str,
    prior_mode: float,
    readout: str,
) -> Dict[str, Any]:
    """Fits observed estimate data of the stimulus 
    feature mean with the method of maximum 
    log(likelihood). This method searches for the 
    model parameters that maximize the log(likeligood) 
    of the observed data given the model.

    Args:
        data (pd.DataFrame): database
        prior_shape (str): shape of the prior  
        - "vonMisesPrior"  
        prior_mode: (float): mode of the prior  

    Returns:
        Dict[str, Any]: results of the fit
    """

    # set parameters
    # (model and task)
    params = get_params(
        database, prior_shape, prior_mode, readout
    )

    # set the data to fit
    data = get_data(database)

    # fit the model
    output = fmin(
        func=get_logl,
        x0=unpack(params["model"]["init_params"]),
        args=(params, *data),
        disp=True,
        retall=True,  # get solutions after iter
        maxiter=100,  # max nb of iterations
        maxfun=100,  # max nb of func eval
        ftol=0.0001,  # objfun convergence
    )

    # get fit results
    best_fit_params = output[0]
    neglogl = output[1]
    return {
        "neglogl": neglogl,
        "best_fit_params": best_fit_params,
    }


def unpack(my_dict: Dict[str, list]) -> list:
    """unpack dict into a flat list

    Args:
        my_dict (Dict[list]): dictionary of list

            e.g., {
                "k_llh": [1,2,3],
                "k_prior": [4,5,6]
            }

    Returns:
        (list): flat list

            e.g., [1,2,3,4,5,6]
    """
    return flatten([my_dict[keys] for keys in my_dict])


def flatten(x: List[list]) -> list:
    """flatten list of list

    Args:
        x (List[list]): list of list

    Returns:
        list: a list
    """
    return [item for sublist in x for item in sublist]


def get_params(
    database: pd.DataFrame,
    prior_shape: str,
    prior_mode: float,
    readout: str,
) -> dict:
    """Set model and task parameters
    free and fixed

    Args:
        database (pd.DataFrame): _description_
        prior_shape (str): _description_
        prior_mode (float): _description_
        readout (str): _description_

    Returns:
        (dict): _description_
    """

    # set model parameters
    # ....................
    # set initial
    model = dict()
    model["init_params"] = {
        "k_llh": [1, 1],
        "k_prior": [1, 1],
        "k_card": [1],
        "prior_tail": [0],
        "p_rand": [0],
        "k_m": [0],
    }

    # set fixed
    model["fixed_params"] = {
        "prior_shape": prior_shape,
        "prior_mode": prior_mode,
        "readout": readout,
    }

    # set task parameters
    # ....................
    # set fixed
    task = dict()
    task["fixed_params"] = {
        "stim_std": database["stim_std"],
        "prior_std": database["prior_std"],
    }
    return {"model": model, "task": task}


def locate_fit_params(
    params: Dict[str, list]
) -> Dict[str, list]:

    """locate fit parameters
    in parameter dictionary

    Args:
        params (Dict[str, list]): parameters

    Returns:
        dict: dictionary of
        the location of each parameter
        type. e.g., 
        
        {
            'k_llh': [0, 1], 
            'k_prior': [2, 3], 
            'k_card': [4], 
            'prior_tail': [5], 
            'p_rand': [6]
        }

    Usage:

        params = {
            'k_llh': [1, 1], 
            'k_prior': [1, 1], 
            'k_card': [0], 
            'prior_tail': [0], 
            'p_rand': [0]
        }
        params_loc = locate_fit_params(params)

    """
    loc = -1
    params_loc = params.copy()

    # loop over parameter types
    for p_type in params:
        params_loc[p_type] = []
        # store each param's index
        for _ in params[p_type]:
            loc += 1
            params_loc[p_type] += [loc]
    return params_loc


def get_data(database: pd.DataFrame):
    """get data to fit

    Args:
        database (pd.DataFrame): _description_

    Returns:
        pd.Series: _description_
    """
    # get stimulus feature mean
    stim_mean = database["stim_mean"]

    # set 0 to 360 deg
    loc_zero = database["estimate"] == 0
    database["estimate"][loc_zero] = 360
    estimate = database["estimate"]
    return stim_mean, estimate


def get_logl(
    fit_p: np.ndarray,
    params: dict,
    stim_mean: pd.Series,
    estimate: pd.Series,
) -> float:
    """calculate the log(likelihood) of the 
    observed stimulus feature mean's estimate
    given the model

    Args:
        fit_p (np.ndarray): model fit parameters
        params (dict): fixed parameters
        stim_mean (pd.Series): stimulus feature mean
        estimate (pd.Series): data estimate to fit

    Returns:
        float: -log(likelihood) of 
            data estimate given model
    """

    # get fixed parameters
    # ....................
    # stimulus
    stim_std = params["task"]["fixed_params"]["stim_std"]
    prior_shape = params["model"]["fixed_params"][
        "prior_shape"
    ]

    # prior
    prior_mode = params["model"]["fixed_params"][
        "prior_mode"
    ]
    prior_std = params["task"]["fixed_params"]["prior_std"]

    # percept readout
    readout = params["model"]["fixed_params"]["readout"]

    # sort stimulus & prior std
    stim_std_set = sorted(np.unique(stim_std), reverse=True)
    prior_std_set = sorted(
        np.unique(prior_std), reverse=True
    )

    # get unique task params
    stim_mean_set = np.unique(stim_mean)
    n_stim_std = len(stim_std_set)
    n_prior_std = len(prior_std_set)

    # count free params
    n_fit_params = sum(~np.isnan(fit_p))

    # get fit parameters
    # ..................
    # locate each type
    params_loc = locate_fit_params(
        params["model"]["init_params"]
    )

    # get params
    k_llh = fit_p[params_loc["k_llh"]]
    k_prior = fit_p[params_loc["k_prior"]]
    k_card = fit_p[params_loc["k_card"]]
    prior_tail = fit_p[params_loc["prior_tail"]][0]
    p_rand = fit_p[params_loc["p_rand"]][0]
    k_m = fit_p[params_loc["k_m"]][0]

    # boolean matrix to locate stim std conditions
    # each column of LLHs is mapped to a
    # stim_std_set
    LLHs = (
        np.zeros((len(stim_std), len(stim_std_set)))
        * np.nan
    )
    for i in range(len(stim_std_set)):
        LLHs[:, i] = stim_std == stim_std_set[i]

    # boolean matrix to locate stim std conditions
    Prior = np.zeros((len(prior_std), n_prior_std)) * np.nan
    for i in range(n_prior_std):
        Prior[:, i] = prior_std == prior_std_set[i]

    # set percept space
    percept_space = np.arange(1, 361, 1)

    # init outputs
    llh_map = defaultdict(dict)

    # store by prior std
    for ix in range(len(prior_std_set)):
        for jx in range(n_stim_std):

            # compute percept density
            # map: maximum a posteriori readouts
            map, llh_map[ix][jx] = get_bayes_lookup(
                percept_space,
                stim_mean_set,
                k_llh[jx],
                prior_mode,
                k_prior[ix],
                k_card,
                prior_tail,
                prior_shape,
                readout=readout,
            )

    # now get matrix 'PupoGivenBI' of likelihood values
    # (upos=1:1:360,trials) for possible values of upo
    # (rows) for each trial (column)
    PupoGivenBI = (
        np.zeros((len(map), len(estimate))) * np.nan
    )
    for ix in range(len(stim_mean_set)):

        # locate stimulus feature mean condition
        thisd = stim_mean == stim_mean_set[ix]

        # locate prior noise condition
        for jx in range(n_prior_std):

            # locate stimulus noise condition
            for kx in range(len(stim_std_set)):

                # locate combined condition
                loc_conditions = np.logical_and(
                    thisd.values, LLHs[:, kx], Prior[:, jx]
                ).astype(bool)
                n_cond_repeat = sum(loc_conditions)
                stim_mean_loc = (
                    stim_mean_set[
                        np.tile(ix, n_cond_repeat)
                    ]
                    - 1
                )
                PupoGivenBI[:, loc_conditions] = llh_map[
                    jx
                ][kx][:, stim_mean_loc]

    # normalize to probabilities
    PupoGivenBI = PupoGivenBI / sum(PupoGivenBI)[None, :]

    # probabilities of percepts "upo" given random estimation
    PupoGivenRand = np.ones((360, len(stim_mean))) / 360

    # calculate probability of percepts "upo" given the model
    PBI = 1 - p_rand
    PupoGivenModel = (
        PupoGivenBI * PBI + PupoGivenRand * p_rand
    )

    # check PupoGivenModel sum to 1
    if not all(sum(PupoGivenModel)) == 1:
        raise ValueError("PupoGivenModel should sum to 1")

    # convolve with motor noise
    # -------------------------
    # Now we shortly replace upo=1:1:360 by upo=0:1:359 because motor noise
    # distribution need to peak at 0 and vmPdfs function needs 'x' to contain
    # the mean '0' to work. Then we set back upo to its initial value. This have
    # no effect on the calculations.
    upo = np.arange(1, 361, 1)
    motor_mean = np.array([360])
    Pmot = VonMises(p=True).get(upo, motor_mean, [k_m])
    Pmot_to_conv = np.tile(Pmot, len(stim_mean))
    PestimateGivenModel = get_circ_conv(
        PupoGivenModel, Pmot_to_conv
    )
    # check that probability of estimates Given Model are positive values.
    # circular convolution sometimes produces negative values very close to zero
    # (order of -10^-18). Those values produce infinite -log likelihood which are
    # only need a single error in estimation to be rejected during model fitting
    # (one trial has +inf -log likelihood to be predicted by the model).
    # This is obviously too conservative. We need a minimal non-zero lapse rate.
    # Prandom that allows for errors in estimation. So we add 10^320 the minimal
    # natural number available in matlab. This means that every time an estimate
    # that is never produced by the model without lapse rate is encountered
    # -loglikelihood increases by -log(10^-320) = 737 and is thus less likely to
    # be a good model (lowest -logLLH). But the model is not rejected altogether
    # (it would be -log(0) = inf). In the end models that cannot account for
    # error in estimates are more likely to be rejected than models who can.
    if not is_empty(np.where(PestimateGivenModel <= 0)[0]):
        PestimateGivenModel[
            PestimateGivenModel <= 0
        ] = 10e-320

    # set upo to initial values any case we use it later
    upo = np.arange(1, 361, 1)

    # normalize to probabilities
    PestimateGivenModel = (
        PestimateGivenModel
        / sum(PestimateGivenModel)[None, :]
    )

    # get the log likelihood of the observed estimates
    # other case are when we just want estimates
    # distributions prediction given
    # model parameters
    if (estimate == 0).any():
        estimate[estimate == 0] = 360

    # single trial's measurement, its position(row)
    # for each trial(col) and its probability
    # (also maxlikelihood of trial's data).
    # make sure sub2ind inputs are the same size
    conditions_loc = np.arange(0, len(stim_mean), 1)
    estimate_loc = estimate.values - 1
    PdataGivenModel = PestimateGivenModel[
        estimate_loc, conditions_loc
    ]

    # sanity checks
    if (PdataGivenModel <= 0).any():
        raise ValueError("""likelihood<0, but must be>0""")
    elif (~np.isreal(PdataGivenModel)).any():
        raise ValueError(
            """likelihood is complex. 
            It should be Real"""
        )

    # We use log likelihood because
    # likelihood is so small that matlab cannot
    # encode it properly (numerical unstability).
    # We can use single trials log
    # likelihood to calculate AIC in the conditions
    # that maximize differences in
    # predictions of two models.
    Logl_pertrial = np.log(PdataGivenModel)

    # we minimize the objective function
    # -sum(log(likelihood))
    negLogl = -sum(Logl_pertrial)

    # akaike information criterion metric
    aic = 2 * (n_fit_params - sum(Logl_pertrial))

    # print
    # [TODO]: add logging here
    print(
        f"""-logl: {negLogl}, aic: {aic}, 
                             k_llh: {k_llh}, 
                             k_prior: {k_prior}, 
                             k_card: {k_card}, 
                             pr_tail: {prior_tail}, 
                             p_rnd: {p_rand},
                             k_m: {p_rand}"""
    )
    return negLogl


def get_bayes_lookup(
    percept_space: np.array,
    stim_mean: np.array,
    k_llh: float,
    prior_mode: float,
    k_prior: float,
    k_card: float,
    prior_tail: float,
    prior_shape: str,
    readout: str,
):
    """Create a bayes lookup matrix
    based on Girshick's paper
    rows: M measurements
    cols: N stimulus feature means
    value: log(likelihood) of percept

    usage:

        percept, logl_percept = get_bayes_lookup(
            percept_space=1:1:360,
            stim_mean=5:10:355,
            k_llh=5,
            prior_mode=225,
            k_prior=4.77,
            k_card=0,
            prior_tail=0,
            prior_shape='von_mises',
            )

    Returns:
        (np.array): percepts
        (np.array): percept likelihood

    [TODO]: clarify the conceptual objects used:
        stimulus space, percept space ... 


    """

    # set stimulus feature mean space s (the
    # discrete circular space with unit 1).
    # e.g., feature could be motion direction
    # s_i are each stimulus feature mean
    stim_mean_space = np.arange(1, 361, 1)

    # cast prior mode as an array
    prior_mode = np.array([prior_mode])

    # calculate measurement densities ~v(s_i,k_llh)
    # (m_i x s_i)
    # m_i is measurement i. percept space
    # is the same as the measurement space
    meas_density = VonMises(p=True).get(
        percept_space, stim_mean, [k_llh]
    )

    # calculate likelihood densities
    # (s space x m_i)
    llh = VonMises(p=True).get(
        stim_mean_space, percept_space, [k_llh]
    )

    # calculate learnt prior densities
    # (s space  x m_i)
    learnt_prior = get_learnt_prior(
        percept_space,
        prior_mode,
        k_prior,
        prior_shape,
        stim_mean_space,
    )

    # calculate posterior densities
    # (s space  x m_i)
    posterior = do_bayes_inference(
        k_llh,
        prior_mode,
        k_prior,
        stim_mean_space,
        llh,
        learnt_prior,
    )

    # choose percepts
    # (m_i x p_i)
    percept, max_nb_percept = choose_percept(
        readout, stim_mean_space, posterior
    )

    # get each percept likelihood
    # for each measurement m_i
    percept, percept_likelihood = get_percept_likelihood(
        percept_space,
        stim_mean,
        stim_mean_space,
        meas_density,
        percept,
        max_nb_percept,
    )
    return percept, percept_likelihood


def get_percept_likelihood(
    percept_space,
    stim_mean,
    stim_mean_space,
    meas_density,
    percept,
    max_nb_percept,
):
    """calculate percepts' likelihood. 
    It is the P(m_i|s_i) of the m_i that produced that data
    map m_i and percept(s) p_i in P(p|m_i)
    P(p|m_i) is important because e.g., when
    a m_i produces a bimodal posterior in response to
    a stimulus (e.g., {flat likelihood, bimodal prior}),
    the two modes are equally likely P(p_1|m_i)
    = P(p_2|mi) = 0.5 and P(p_1|s_i) =
    P(p_1|s_i) = P(p_1|m_i)*P(m_i|s_i)
    = 0.5*P(m_i|s_i). Similarly, P(p_2|s_i) =
    P(p_2|m_i)*P(m_i|s_i) = 0.5*P(m_i|s_i).
    The P(p|m_i) of each percept observed for a
    m_i is 1/len(p).
    percepts only depend on m_i which determines likelihood.
    The displayed stimulus determines percept probability.
    Percepts per m_i (rows) are the same across stimulus
    feature means (cols). m_i rows are repeated in the matrix
    when a m_i produces many percepts.
    e.g., the matrices for a max number of percept per m_i=2
    
       mPdfs_p_1 . . s_S
           .
           .
          m_i_M
       mPdfs_p_2 . . s_S
           .
           .
          m_i_M
           .
           .

    Args:
        percept_space (_type_): _description_
        stim_mean (_type_): _description_
        stim_mean_space (_type_): _description_
        meas_density (_type_): _description_
        percept (_type_): _description_
        max_nb_percept (_type_): _description_

    Returns:
        _type_: _description_
    """

    # count percepts by m_i
    # (m_i x 0)
    max_nb_pi_given_mi = np.sum(~np.isnan(percept), 1)

    # probability of percepts given m_i
    # p(p_i|m_i)
    # (m_i x 1)
    prob_pi_given_mi = 1 / max_nb_pi_given_mi

    # assign equiprobability to percepts with
    # same m_i (across cols)
    # (m_i x p_i)
    prob_pi_given_mi = np.tile(
        prob_pi_given_mi[:, None], max_nb_percept
    )

    # reshape as column vector (column-major)
    # (m_i*p_i x s_i)
    prob_pi_given_mi = prob_pi_given_mi.flatten("F")
    prob_pi_given_mi = np.tile(
        prob_pi_given_mi[:, None], len(stim_mean)
    )

    # associate P(m_i|s_i) of each m_i (row)
    # for each stimulus feature mean s_i(col)
    # e.g., the matrices for a max number of
    # percept per m_i = 2
    #
    #    mPdfs_percept1 . . dir_D
    #        .
    #        .
    #       mi_M
    #    mPdfs_percept2 . . dir_D
    #        .
    #        .
    #       mi_M
    # (x si)
    prob_mi_given_si = np.tile(
        meas_density, (max_nb_percept, 1)
    )

    # reshape as column vector (column-major)
    flatten_percept = percept.flatten("F")[:, None]

    # create a percept space
    # to map with likelihood values
    u_l = np.tile(percept_space[:, None], max_nb_percept)

    # reshape as column vector (column-major)
    u_l = u_l.flatten("F")[:, None]

    # map percept and its likelihood
    # to sort by percept
    to_sort = np.hstack(
        [
            u_l,
            flatten_percept,
            prob_pi_given_mi,
            prob_mi_given_si,
        ]
    )

    # sort by percept
    to_sort = to_sort[to_sort[:, 1].argsort()]

    # unpack
    u_l = to_sort[:, 0][:, None]
    percept = to_sort[:, 1][:, None]
    prob_pi_given_mi = to_sort[:, 2 : 2 + len(stim_mean)]
    prob_mi_given_si = to_sort[:, 2 + len(stim_mean) :]

    # likelihood of percepts given stimulus
    # p(p_i|s_i)
    prob_pi_given_si = prob_pi_given_mi * prob_mi_given_si

    # Set the likelihood=0 for percepts not produced
    # because the model cannot produce those percepts
    # even at a reasonable resolution of stimulus feature
    # mean
    percept_set = np.unique(percept[~np.isnan(percept)])
    missing_pi = np.array(
        tuple(set(percept_space) - set(percept_set))
    )[:, None]
    nb_missing_pi = len(missing_pi)

    # Add unproduced percept and set their
    # likelihood=0, then re-sort by percept
    prob_missing_pi_given_si = np.zeros(
        (nb_missing_pi, len(stim_mean))
    )
    prob_all_pi_given_si = np.vstack(
        [prob_pi_given_si, prob_missing_pi_given_si]
    )
    all_pi = np.vstack([percept, missing_pi])
    missing_u_l = np.zeros((nb_missing_pi, 1)) * np.nan
    u_l = np.vstack([u_l, missing_u_l])

    # map all objects to sort them
    to_sort = np.hstack([u_l, all_pi, prob_all_pi_given_si])

    # sort by percept
    to_sort = to_sort[to_sort[:, 1].argsort()]
    all_pi = to_sort[:, 1]
    prob_all_pi_given_si = to_sort[:, 2:]

    # likelihood of each percept (rows are percepts, cols are motion directions,
    # values are likelihood). When a same percept has been produced by different
    # mi produced by the same motion direction, then the percept's likelihood is
    # its mi likelihood.  The likelihoods are properly scaled at the end to sum
    # to 1. e.g.,
    # ................................................................................
    #    if only mi_1 produces?percept=100? and mi_2 also produces?percept=100?
    #  ?and mi_1 and mi_2 are both produced by the same motion direction di
    #    P(percept|di) = P(percept|mi_1)*P(mi_1|di) + P(percept|mi_2)*P(mi_2|dir)
    #    P(percept|mi_1) = P(percept|mi_1) = 1 because both mi only produce one percept
    #    (the same)
    #    so P(percept|di) = P(mi_1|di) + P(mi_2|dir)
    # ................................................................................
    #
    # note: we can see horizontal stripes of 0 likelihood near the obliques when
    # cardinal prior is strong because obliques percepts are never produced.
    # The range of percepts not produced near the obliques increase significantly
    # with cardinal prior strength.
    percept = np.unique(all_pi[~np.isnan(all_pi)])
    prob_pi_set_given_si = (
        np.zeros([len(percept), len(stim_mean)]) * np.nan
    )

    # find measurements that produced this same percept
    # and average probabilities over evidences mi that
    # produces this same percept
    for ix in range(len(percept)):
        loc_pi_set = all_pi == percept[ix]
        prob_pi_set_given_si[ix, :] = sum(
            prob_all_pi_given_si[loc_pi_set, :], 0
        )
    prob_pi_set_given_si[np.isnan(prob_pi_set_given_si)] = 0

    # calculate likelihood of each
    # unique percept
    # matrix of percepts (rows) x
    # 360 stimulus mean space (cols)
    percept_likelihood = (
        np.zeros((len(percept), len(stim_mean_space)))
        * np.nan
    )
    stim_mean_loc = stim_mean - 1
    percept_likelihood[
        :, stim_mean_loc
    ] = prob_pi_set_given_si

    # normalize to probability
    percept_likelihood = (
        percept_likelihood
        / sum(percept_likelihood)[None, :]
    )
    return percept, percept_likelihood


def choose_percept(
    readout: str,
    stim_mean_space: np.ndarray,
    posterior: np.ndarray,
):
    """choose percept(s) for each
    measurement m_i produced by a stimulus
    s_i

    Args:
        readout (str): the posterior readout
        - 'map': maximum a posteriori decision
        stim_mean_space (np.ndarray): the space
            of stimulus feature mean (e.g., motion 
            directions)
        posterior (np.ndarray): the posterior 

    Raises:
        ValueError: _description_
        NotImplementedError: _description_
        ValueError: _description_

    Returns:
        (np.ndarray): percept 
        (int): max_n_percept 
        ul
    """

    # choose a percept p_i (readout)
    # (s_i x p_i)
    # the measurement space is assumed to
    # be the same as the stimulus feature space
    meas_space_size = len(stim_mean_space)
    stim_space_size = len(stim_mean_space)
    percept = (
        np.zeros((stim_space_size, meas_space_size))
        * np.nan
    )

    # when the readout is maximum-a-posteriori
    if readout == "map":

        # find the maximum-a-posteriori estimate(s)(maps)
        # mapped with each m_i (rows). A m_i can produce
        # many maps (many cols for a row) .e.g., when both
        # likelihood and learnt prior are weak, an evidence
        # produces a relatively flat posterior which maximum
        # can not be estimated accurately. max(posterior)
        # produces many maps with equal probabilities.

        # map each m_i with its percept(s)
        for meas_i in range(meas_space_size):

            # locate each posterior's maximum
            # a posteriori(s)
            loc_percept = posterior[:, meas_i] == np.max(
                posterior[:, meas_i]
            )

            # count number of percepts
            n_percepts = sum(loc_percept)

            # map measurements (rows)
            # with their percepts (cols)
            percept[meas_i, :n_percepts] = stim_mean_space[
                loc_percept
            ]

            # handle exception
            # check that all measurements have at
            # least a percept
            if n_percepts == 0:
                raise ValueError(
                    f"""Measurement {meas_i}
                    has no percept(s)."""
                )
    else:
        # handle exception
        raise NotImplementedError(
            f"""
            Readout {readout} has not 
            yet been implemented. 
            """
        )

    # replace 0 by 360 degree
    percept[percept == 0] = 360

    # handle exception
    is_percept = percept[~np.isnan(percept)]
    if (is_percept > 360).any() or (is_percept < 1).any():
        raise ValueError(
            """Percepts must belong to [1,360]."""
        )

    # drop nan percepts from cols
    # (m_i x max_nb_percept)
    max_nb_percept = max(np.sum(~np.isnan(percept), 1))
    percept = percept[:, :max_nb_percept]
    return percept, max_nb_percept


def get_learnt_prior(
    percept_space: np.ndarray,
    prior_mode: np.ndarray,
    k_prior: float,
    prior_shape: str,
    stim_mean_space,
):
    """calculate the learnt prior probability 
    distribution
    cols: prior for each m_i, are the same
    rows: stimulus feature mean space (e.g.,
    motion direction) 

    Args:
        percept_space (np.ndarray): _description_
        prior_mode (np.ndarray): _description_
        k_prior (float): _description_
        prior_shape (str): shape of the prior
        - 'vonMisesPrior'
        stim_mean_space (np.ndarray): stimulus 
        feature mean space: (1:1:360)

    Returns:
        (np.ndarray): matrix of learnt priors
        rows: stimulus feature mean space
        cols: m_i
    """
    if prior_shape == "vonMisesPrior":
        # create prior density
        # (Nstim mean x 1)
        learnt_prior = VonMises(p=True).get(
            stim_mean_space, prior_mode, [k_prior],
        )
        # repeat the prior across cols
        # (Nstim mean x Nm_i)
        learnt_prior = np.tile(
            learnt_prior, len(percept_space)
        )
    return learnt_prior


def do_bayes_inference(
    k_llh,
    prior_mode,
    k_prior,
    stim_mean_space,
    llh,
    learnt_prior,
):

    """Realize Bayesian inference    
    """

    # do Bayesian integration
    posterior = llh * learnt_prior

    # normalize cols to sum to 1
    posterior = posterior / sum(posterior)[None, :]

    # round posteriors
    # We fix probabilities at 10e-6 floating points
    # We can get posterior modes despite round-off errors
    # We tried with different combinations of 10^6 and
    # round instead of fix. If we don't round enough we
    # cannot get the modes of the posterior accurately
    # because of round-off errors. If we round too much
    # we get more modes than we should, but the values
    # obtained are near the true modes so I choose to round
    # more (same as in simulations).
    # sum over rows
    posterior = np.round(posterior, 6)

    # TRICK: When k gets very large, e.g., for the prior,
    # most values of the prior becomes 0 except close to
    # the mean. The product of the likelihood and prior
    # only produces 0 values for all directions, particularly
    # as motion direction is far from the prior. Marginalization
    # (scaling) makes them NaN. If we don't correct for that,
    # fit is impossible. In reality a von Mises density will
    # never have a zero value at its tails. We use the closed-from
    # equation derived by Murray and Morgenstern, 2010.
    loc = np.where(np.isnan(posterior[0, :]))[0]
    if not is_empty(loc):
        # use Murray and Morgenstern., 2010
        # closed-form equation
        # mode of posterior
        mi = stim_mean_space[loc]
        mirad = get_deg_to_rad(mi, True)
        uprad = get_deg_to_rad(prior_mode, True)

        # set k ratio
        k_ratio = k_llh / k_prior
        if k_llh == k_prior == np.inf:
            k_ratio = 1
        else:
            raise Exception("Check k_prior or k_llh")

        upo = np.round(
            mirad
            + arctan2(
                sin(uprad - mirad),
                k_ratio + cos(uprad - mirad),
            )
        )
        # make sure upo belongs to stimulus
        # mean space
        upo = np.round(get_rad_to_deg(upo))

        if k_llh == np.inf or k_prior == np.inf:
            kpo = np.sqrt(
                k_llh ** 2
                + k_prior ** 2
                + 2 * k_prior * k_llh * cos(uprad - mirad)
            )
            raise Exception(
                """We have not yet solved Bayesian
                 integration when k_llh or k_prior is 
                 +inf"""
            )

        # create those posterior
        posterior[:, loc] = VonMises(p=True).get(
            stim_mean_space, upo, [kpo],
        )
    return posterior
