# -*- coding: utf-8 -*-
import os
import sys

import numpy as np
import scipy.special as special
from functools import partial
import matplotlib.pyplot as plt
import matplotlib.animation as animation

import classes.Curvilinear as Curvilinear

import helpers.rootfinder as roots
import helpers.Property as Property
import helpers.LaPlace_asymptotes as asym
import helpers.gravity_functions as grav


def blockprint():
    sys.stdout = open(os.devnull, 'w')

def enableprint():
    sys.stdout = sys.__stdout__


def rootfind_dimless(mode_admin, verbose=False, inc=1.0033, rsearch=False):
    """
    For a given m, k and qlist, and potentially for different radius, mass and
    period as well, determines the wave mode and calculates the eigenvalues
    from the asymptotically calculated values.
    """
    qlist, found_lamlist = roots.multi_rootfind_fromguess_dimless(mode_admin, verbose=False, inc=inc, rsearch=rsearch)
    return mode_admin.guess, found_lamlist, mode_admin.mode.split("_")[0], mode_admin.direction


def houghHat(s, sig):
    hermite = special.eval_hermite(s, sig)
    exp = np.exp(-(sig**2)/2.)
    return hermite*exp


def hough(s, sig, m, lam, q):
    L = lam**.5
    Lnu = L*q
    prefactor = np.sqrt(Lnu) / (lam - m**2)
    minhermite = s*((m/L) + 1) * special.eval_hermite(s-1, sig)
    maxhermite = .5*((m/L) - 1) * special.eval_hermite(s+1, sig)
    exp = np.exp(-(sig**2)/2.)
    hermites = minhermite+maxhermite
    return prefactor * hermites * exp


def houghTilde(s, sig, m, lam, q):
    L = lam**.5
    Lnu = L*q
    prefactor = m*np.sqrt(Lnu) / (m**2 - L**2)
    minhermite = s*((L/m) + 1) * special.eval_hermite(s-1, sig)
    maxhermite = .5*((L/m) - 1) * special.eval_hermite(s+1, sig)
    exp = np.exp(-(sig**2)/2.)
    hermites = minhermite+maxhermite
    return prefactor * hermites * exp


def kelvinhough(mu, m, q):
    min_mq_root = (-m*q)**.5
    tau = min_mq_root * mu
    return np.exp(-(tau**2)/2.)
    

def kelvinhoughHat(mu, m, q):
    min_mq_root = (-m*q)**.5
    tau = min_mq_root * mu
    fst = 1./min_mq_root
    snd = -(m*m) / (2*m*q + 1.)
    thr = tau * np.exp(-(tau**2)/2.)
    return fst * snd * thr


def kelvinhoughTilde(mu, m, q):
    min_mq_root = (-m*q)**.5
    tau = min_mq_root * mu
    fst = -m
    brckt = tau*tau / (2*m*q + 1) + 1
    exp = np.exp(-(tau**2)/2.)
    return fst * brckt * exp


def numerics(ode_class, ode_args, lam, N):
    ode_solver = ode_class.solver_t_dimless(*ode_args)

    steps = np.linspace(ode_class.t0, ode_class.t1, N)
    [P, Q] = ode_solver.interp(lam, steps)
    return P, Q


def normalize(array):
    return array/max(np.abs(array))


def townsendify(hough, houghhat, houghtilde, k, m):
    if k%2 == 0:
        divisor = hough[-1]
    else:
        divisor = -houghhat[-1]
    if m < 0:
        houghtilde *= -1
    return hough/divisor, houghhat/divisor, houghtilde/divisor


def make_houghs(m, k, s, q, ecc, chi, gravfunc):
    N = 125

    dlngrav=partial(gravfunc, chi)
    mode_admin = Property.Mode_admin(m, k)
    mode_admin.set_qlist(np.asarray([q]))
    mode_admin.set_curvilinear(ecc, chi, dlngrav)

    guess, lam, wavename, direc = rootfind_dimless(mode_admin, verbose=False, inc=1.075, rsearch=False)
    mu = np.linspace(1., 0., N)
    L = lam**.5
    Lnu = L * q  # it should just be q but that breaks if q is negative?
    sig = np.sqrt(Lnu) * mu
    guesssig = np.sqrt(guess**.5 * q) * mu

    print "Lnu: {}, guessLnu: {}".format(Lnu, (guess**.5) * q)
    print "k: {}, s: {}, q: {}".format(k, s, q)

    # Numeric values
    is_even = Curvilinear.check_is_even(m, k)
    num_hough, num_houghHat = numerics(Curvilinear, [mode_admin, q], lam, N)
    num_houghTilde = -m * num_hough - q*mu * num_houghHat

    ## Analytic values
    ana_houghHat = houghHat(s, guesssig)
    ana_hough = hough(s, guesssig, m, guess, q)
    ana_houghTilde = houghTilde(s, guesssig, m, guess, q)
    if wavename == "kelvin mode":
        ana_houghHat = kelvinhoughHat(mu, m, q)
        ana_hough = kelvinhough(mu, m, q)
        ana_houghTilde = kelvinhoughTilde(mu, m, q)

    num_hough, num_houghHat, num_houghTilde = townsendify(num_hough, num_houghHat, num_houghTilde, k, m)
    ana_hough, ana_houghHat, ana_houghTilde = townsendify(ana_hough, ana_houghHat, ana_houghTilde, k, m)

    fig = plt.figure()
    ax1 = fig.add_subplot(3, 1, 1)
    ax1.set_title("m: {}, k: {}, s: {}, q: {}  ({}grade {}); ecc: {}, $\chi$: {}".format(m, k, s, q, direc, wavename, ecc, chi))
    ax1.plot(mu, num_hough, ls="--", label="Numeric")
    ax1.plot(mu, ana_hough, label="Analytic")
    ax1.set_ylabel(r"$\Theta(\sigma)$")
    ax1.set_xlim([0, 1])
    ax2 = fig.add_subplot(3, 1, 2)
    ax2.plot(mu, num_houghHat, ls="--")
    ax2.plot(mu, ana_houghHat)
    ax2.set_ylabel(r"$\hat\Theta(\sigma)$")
    ax2.set_xlim([0, 1])
    ax3 = fig.add_subplot(3, 1, 3)
    ax3.plot(mu, num_houghTilde, ls="--")
    ax3.plot(mu, ana_houghTilde)
    ax3.set_ylabel(r"$\tilde\Theta(\sigma)$")
    ax3.set_xlabel(r"$\mu \equiv \cos(\theta)$")
    ax3.set_xlim([0, 1])

    ax1.tick_params(axis='y', which='both', left='on', right='on')
    ax2.tick_params(axis='y', which='both', left='on', right='on')
    ax3.tick_params(axis='y', which='both', left='on', right='on')
    ax1.legend()
    plt.show()


def eccentricity_compare(m, k, s, q, ecclist, chilist, gravfunc):
    if len(ecclist) != len(chilist):
        raise ValueError("Warning: ecclist and chilist should be the same length!")
    N = 125

    mode_admin = Property.Mode_admin(m, k)
    mode_admin.set_qlist(np.asarray([q]))

    fig = plt.figure()
    ax1 = fig.add_subplot(3, 1, 1)
    ax2 = fig.add_subplot(3, 1, 2)
    ax3 = fig.add_subplot(3, 1, 3)
    ax1.set_xlim([0, 1])
    ax2.set_xlim([0, 1])
    ax3.set_xlim([0, 1])
    ax1.set_ylabel(r"$\Theta(\sigma)$")
    ax2.set_ylabel(r"$\hat\Theta(\sigma)$")
    ax3.set_ylabel(r"$\tilde\Theta(\sigma)$")
    ax3.set_xlabel(r"$\mu \equiv \cos(\theta)$")

    for ecc, chi in zip(ecclist, chilist):
        dlngrav=partial(gravfunc, chi)
        mode_admin.set_curvilinear(ecc, chi, dlngrav)
        guess, lam, wavename, direc = rootfind_dimless(mode_admin, verbose=False, inc=1.075, rsearch=False)
        mu = np.linspace(1., 0., N)
        sigma = np.sqrt(1-((ecc**2.)*(1-mu**2)))

        # Numeric values
        is_even = Curvilinear.check_is_even(m, k)
        num_hough, num_houghHat = numerics(Curvilinear, [mode_admin, q], lam, N)
        num_houghTilde = -m * num_hough - q*mu/sigma * num_houghHat

        ax1.set_title("m: {}, k: {}, s: {}, q: {}  ({}grade {})".format(m, k, s, q, direc, wavename))
        ax1.plot(mu, num_hough, label=r"ecc: {}, $\chi$: {}".format(ecc, chi))
        ax2.plot(mu, num_houghHat)
        ax3.plot(mu, num_houghTilde)

    ax1.tick_params(axis='y', which='both', left='on', right='on')
    ax2.tick_params(axis='y', which='both', left='on', right='on')
    ax3.tick_params(axis='y', which='both', left='on', right='on')
    ax1.legend()
    plt.show()


def eccentricity_movie(m, k, s, q, eccstart, eccend, frames, gravfunc, fixframe=False, moviesaving=False, town_normalize=False):
    """
    Creates a movie at a set m, k and q for "frames" steps between eccstart and eccend.
    Will assume chi = 2*(ecc**2)
    """
    N = 125

    mode_admin = Property.Mode_admin(m, k)
    mode_admin.set_qlist(np.asarray([q]))
    direc = mode_admin.get_direction()
    mode = mode_admin.get_wavemode(direc)
    ecclist = np.linspace(eccstart, eccend, frames)
    subdir = "data/moviedata/{}_{}_{}_{}_{}_{}_{}_{}".format(str(m), str(k), str(s), str(q), str(eccstart), str(eccend), str(frames), str(town_normalize))

    fig = plt.figure()
    ax1 = fig.add_subplot(3, 1, 1)
    ax2 = fig.add_subplot(3, 1, 2)
    ax3 = fig.add_subplot(3, 1, 3)
    mu = np.linspace(1., 0., N)
    if fixframe:
        savestring = subdir + "/{}_{}_{}".format(0.0, 0.0, str(gravfunc.__name__))
        data = np.loadtxt(savestring)
        num_hough_init, num_houghHat_init, num_houghTilde_init = data
        ax1lim = [min(num_hough_init)*1.1, max(num_hough_init)*1.2]
        ax2lim = [min(num_houghHat_init)*1.1, max(num_houghHat_init)*1.2]
        ax3lim = [min(num_houghTilde_init)*1.1, max(num_houghTilde_init)*1.2]

    def update(i):
        ecc = ecclist[i]
        chi = 2. * (ecc**2.)
        savestring = subdir + "/{}_{}_{}".format(str(ecc), str(chi), str(gravfunc.__name__))
        data = np.loadtxt(savestring)
        num_hough, num_houghHat, num_houghTilde = data

        # Clear the subplots
        ax1.cla()
        ax2.cla()
        ax3.cla()

        ax1.set_xlim([0, 1])
        ax2.set_xlim([0, 1])
        ax3.set_xlim([0, 1])
        ax1.set_ylabel(r"$\Theta(\sigma)$")
        ax2.set_ylabel(r"$\hat\Theta(\sigma)$")
        ax3.set_ylabel(r"$\tilde\Theta(\sigma)$")
        ax3.set_xlabel(r"$\mu \equiv \cos(\theta)$")
        if fixframe:
            ax1.plot(mu, num_hough_init, ls="--", label="Spherical")
            ax2.plot(mu, num_houghHat_init, ls="--")
            ax3.plot(mu, num_houghTilde_init, ls="--")
            ax1.set_ylim(ax1lim)
            ax2.set_ylim(ax2lim)
            ax3.set_ylim(ax3lim)

        ax1.set_title("m: {}, k: {}, s: {}, q: {}  ({}grade {}), ecc: {:.4f}, $\chi$: {:.4f}".format(m, k, s, q, direc, mode, ecc, chi))
        ax1.plot(mu, num_hough, label="Curvilinear")
        ax2.plot(mu, num_houghHat)
        ax3.plot(mu, num_houghTilde)
        ax1.legend()

    
    # Set up formatting for the movie files
    Writer = animation.writers['ffmpeg']
    writer = Writer(fps=30, metadata=dict(artist='Bart'), bitrate=750)

    ani = animation.FuncAnimation(fig, update, frames=frames, interval=20, repeat=False)
    if moviesaving:
        tardir = "data/movies/{}_{}".format(str(direc), mode.replace(" ", "_"))
        if not os.path.exists(tardir):
            os.makedirs(tardir)
        name = "/{}_{}_{}_{}_{}_{}_{}".format(str(eccstart), str(eccend), str(frames), str(m), str(k), str(q), str(town_normalize))
        print "Saving file to: {}.mp4".format(tardir+name)
        ani.save(tardir+"{}.mp4".format(name), writer=writer)
    else:
        plt.show()


def create_data(m, k, s, q, eccstart, eccend, frames, gravfunc, town_normalize=False):
    N = 125

    mode_admin = Property.Mode_admin(m, k)
    mode_admin.set_qlist(np.asarray([q]))
    ecclist = np.linspace(eccstart, eccend, frames)
    subdir = "data/moviedata/{}_{}_{}_{}_{}_{}_{}_{}".format(str(m), str(k), str(s), str(q), str(eccstart), str(eccend), str(frames), str(town_normalize))
    if not os.path.exists(subdir):
        os.makedirs(subdir)

    for i in range(len(ecclist)):
        ecc = ecclist[i]  # This way its ensured you read out the files in the proper order!
        chi = 2. * (ecc**2.)
        dlngrav = partial(gravfunc, chi)
        mode_admin.set_curvilinear(ecc, chi, dlngrav)
        lam, wavename, direc = rootfind_dimless(mode_admin, verbose=False, inc=1.075, rsearch=False)[1:]

        mu = np.linspace(1., 0., N)
        sigma = np.sqrt(1-((ecc**2.)*(1-mu**2)))
        num_hough, num_houghHat = numerics(Curvilinear, [mode_admin, q], lam, N)
        num_houghTilde = -m * num_hough - q*mu/sigma * num_houghHat

        if town_normalize:
            num_hough, num_hougHat, num_houghTilde = townsendify(num_hough, num_houghHat, num_houghTilde, k, m)

        data = np.asarray([num_hough, num_houghHat, num_houghTilde])
        savestring = subdir + "/{}_{}_{}".format(str(ecc), str(chi), str(gravfunc.__name__))
        np.savetxt(savestring, data)


if __name__ == "__main__":
#    m, k, s, q = -2, 2, 1, 3  # Pro g mode
#    m, k, s, q = 2, 2, 3, 3  # Retro g mode
#    m, k, s, q = 2, 1, 2, 3  # Retro g mode
#    m, k, s, q = 2, 0, 1, 3  # Retro g mode
#    m, k, s, q = -2, 1, 0, 3  # Pro Yanai
#    m, k, s, q = 2, -1, 0, 6  # Retro Yanai
    m, k, s, q = 2, -2, 1, 30  # Retro r mode
#    m, k, s, q = -2, 0, -1, 3  # Kelvin check - this should use different functions!
#    m, k, s, q = -2, 0, -1, 10  # LeeSaio1997 check - these do not require new functions ?

    ecc = 0.
    chi = 2. * (ecc**2)
#    make_houghs(m, k, s, q, ecc, chi, grav.chi_gravity_deriv)

    ecclist = np.asarray([0., 0.05, .1, .15, .25])
    chilist = 2. * (ecclist**2)
#    eccentricity_compare(m, k, s, q, ecclist, chilist, grav.chi_gravity_deriv)

    # To reproduce the Townsend plots 
    mlist = [-2, 2, -2, 2, -2, 2, 2, 2]
    klist = [2, 2, 1, 1, 0, 0, -1, -2]
    slist = [1, 3, 0, 2, -1, 1, 0, 1]
    qlist = [3, 3, 3, 3, 3, 3, 6, 15]
    ecc, chi, gravfunc = 0., 0., grav.chi_gravity_deriv

#    for m, k, s, q in zip(mlist, klist, slist, qlist):
#        make_houghs(m, k, s, q, ecc, chi, gravfunc)

#    m, k, s, q = 2, -2, 1, 16.
#    m, k, s, q = 2, 2, 3, 3
    m, k, s, q = 1, -2, 1, 400  # realistic r-mode since m=1
    eccstart, eccend, frames = 0., .5, 500
    gravfunc = grav.chi_gravity_deriv
    town_normalize = True  # To use townsend's normalization setup
#    create_data(m, k, s, q, eccstart, eccend, frames, gravfunc, town_normalize=town_normalize)
    eccentricity_movie(m, k, s, q, eccstart, eccend, frames, gravfunc, fixframe=True, moviesaving=False, town_normalize=town_normalize)



