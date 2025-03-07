"""Solve ODE for LaPlace Tidal Equations:

  (1 - x^2) \diffrac{f}{x} = (2*alpha*x + m*q*x) * f + (q^2 * m^2 - 1) * g
  (1 - x^2) \diffrac{g}{x} = (2*alpha*x - m*q*x) * g + (lambda*(1-x^2) - m^2)*f

with

  P = (1 - x^2) f
  Q = (1 - x^2) g


to avoid singularity and implement boundary condition at \pm 1"""

import numpy as np

from scipy.integrate import ode
from scipy.integrate import odeint
from scipy.interpolate import interp1d

import Observers

## -------------------------------------------------------------------------- ##

eps = 1.0e-6
t0 = 1. - eps
t1 = 0.

def norm (arr):
    fmax = np.amax(arr)
    fmin = np.amin(arr)
    if abs(fmax) > abs(fmin):
        return fmax
    else:
        return fmin

def check_is_even (m, l):
    if (m+l) % 2 == 0:
        return True
    else:
        return False

def is_even_str (is_even):
    if is_even is True:
        return "even"
    else:
        return "odd"

def eigval (l):
    return l*(l+1.0)

## -------------------------------------------------------------------------- ##

class ODE_t:
    """Return RHS of ODE, and helpful functions for transformation"""
    def __init__ (self, m, q, lam):
        self.m = 1. * m
        self.q = 1. * q
        self.msq = m*m
        self.qsq = q*q

        self.alpha = .5 * abs(self.m)
        self.lam = 1. * lam

    def init_y (self):
        y0 = 1.0e-4
        y1 = (2 * self.alpha + self.m * self.q)*t0*y0/(1 - t0*t0*self.qsq)
        return [y0, y1]  # Starting point, variation of RHS of eq (10)

    def coeffs (self, t):
        ## TODO: update as this is now LaPlace, not Legendre!
        sinsq = 1. - t*t
        twoax = 2. * self.alpha * t
        return np.array([twoax / sinsq, -1. / sinsq, self.lam - self.msq / sinsq, twoax / sinsq])

    def __call__ (self, t, y):
    # Comments show what variables are called in legendre-ode_derivation.pdf
        sinsq = 1. - t*t  # 1-(x**2) (\equiv 1-\mu^2 \equiv sin^2 => name)
        twoax = 2. * self.alpha * t  # 2*alpha*x
        mqx = self.m * self.q * t  # m*q*x
        qxsqmo = (self.qsq * t*t) - 1  # (x**2 * q**2) - 1
        dy0dt = ( (twoax + mqx)*y[0] + qxsqmo*y[1] ) / sinsq  # eq (8), rewritten
#        dy1dt = ( (self.lam*sinsq - self.msq)*y[0] + (twoax - mqx)*y[1] ) / sinsq
        dy1dt = self.lam*y[0] - (self.msq*y[0] - (twoax - mqx)*y[1]) / sinsq  # eq(9), rewritten
        return [dy0dt, dy1dt]

    def transform (self, steps, solun):
        for t, y in zip(steps, solun):
            one_m_xsq_a = np.power(1. - t*t, self.alpha)
            y *= one_m_xsq_a

def run_ode (leg, obs):
    """Shoot the ode for given m and observer. Could implement 
    this as an object"""
    # stepper = 'dopri5'
    stepper = 'dop853'
    atol = 0.
    rtol = 1./(2**30)
    nsteps = 2000
    y0 = leg.init_y()
    solver = ode(leg)
    solver.set_integrator(stepper, atol=atol, rtol=rtol, nsteps=nsteps)
    solver.set_solout(obs)
    solver.set_initial_value(y0, t0)
    return solver.integrate(t1)

## -------------------------------------------------------------------------- ##

class score_t:
    """Provide f or g depending on odd or even"""
    def __init__ (self, is_even):
        self.idx = self.set_idx(is_even)
    def set_idx (self, is_even):
        if is_even is True:
            return 1
        return 0
    def __call__ (self, y1):
        return y1[self.idx]

## -------------------------------------------------------------------------- ##

class solver_t:
    """Shoot for x=0 from x=1-eps, can also save eigenvalues of solution"""
    def __init__ (self, m, q, is_even):
        self.m = m
        self.q = q
        self.score = score_t(is_even)

    def set_m (self, m):
        self.m = m

    def set_is_even (self, is_even):
        self.score.set_idx(is_even)

    def shoot (self, lam):
        leg = ODE_t(self.m, self.q, lam)
        obs = Observers.max_t()
        y1 = run_ode(leg, obs)
        return self.score(y1 / obs.max_f)

    def __call__ (self, lam):
        return self.shoot(lam)

    def save (self, lam):
        leg = ODE_t(self.m, self.q, lam)
        obs = Observers.save_t()
        run_ode(leg, obs)
        steps = obs.steps()
        solun = obs.solun()
        leg.transform(steps, solun)
        N = norm(solun[:,0])
        return steps, solun / N

    def interp (self, lam, steps):
        """note: interpolation is performed using cubic spline.
        Should probably check how scipy.integrate.solve_ivp interpolates;
        possibly uses dense output stepper for interpolation"""
        t_interp, y_interp = self.save(lam)
        P = interp1d(t_interp, y_interp[:,0], kind='cubic')
        Q = interp1d(t_interp, y_interp[:,1], kind='cubic')
        return np.array([P(steps), Q(steps)])

