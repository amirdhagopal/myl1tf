# Adapted from py-l1tf here https://github.com/elsonidoq/py-l1tf/
from itertools import chain
from cvxopt import matrix, spmatrix, solvers,sparse
import numpy as np
solvers.options['show_progress'] = 0


def get_second_derivative_matrix(n):
    """
    :param n: The size of the time series

    :return: A matrix D such that if x.size == (n,1), D * x is the second derivative of x
    """
    m = n - 2

    D = spmatrix(list(chain(*[[1, -2, 1]] * m)),
                 list(chain(*[[i] * 3 for i in xrange(m)])),
                 list(chain(*[[i, i + 1, i + 2] for i in xrange(m)])))
    return D

def l1tf(corr, alpha, primary=False):
    """
    :param corr: Corrupted signal, should be a numpy array / pandas Series
    :param alpha: Strength of regularization
    :param primary : if True will use Primary rather than Dual space , default False
    :return: The filtered series
    This uses numpy arrays, a wrapper for the one using cvxopt version which
    returns cvxopt matrices.
    """

    # scaling things to standardized size
    m = float(corr.min())
    M = float(corr.max())
    denom = M - m
    # if denom == 0, corr is constant
    t = (corr - m) / (1 if denom == 0 else denom)

    assert isinstance(corr, np.ndarray)
    solver_func = l1tf_cvxopt_primary if primary else l1tf_cvxopt
    sol = solver_func(matrix(t), alpha)
    res = np.asarray(sol * (M - m) + m).squeeze()
    return res


def l1tf_cvxopt(corr, alpha,period=0):
    """
        minimize    (1/2) * ||x-corr||_2^2 + alpha * sum(y)
        subject to  -y <= D*x <= y

    Variables x (n), y (n-2).

    :param corr: corrupted data being fit
    :param alpha: regularization parameter
    :return: The fit in cvxopt matrix.
    Solves in the Dual problem space
    """

    n = corr.size[0]
    m = n - 2

    D = get_second_derivative_matrix(n)

    P = D * D.T
    q = -D * corr

    G = spmatrix([], [], [], (2 * m, m))
    G[:m, :m] = spmatrix(1.0, range(m), range(m))
    G[m:, :m] = -spmatrix(1.0, range(m), range(m))

    h = matrix(alpha, (2 * m, 1), tc='d')

    res = solvers.qp(P, q, G, h)

    return corr - D.T * res['x']


def construct_seasonal_design_matrix(n, period):
    """
    :param n: number of data points in time series
    :param period: period of seasonality
    :return:
    """

    num_cycles = n/period
    num=n+period
    num_extra = n - period*num_cycles
    identity_n = spmatrix(1.0, range(n), range(n))
    identity_p = spmatrix(1.0, range(period), range(period))
    P = spmatrix(0.0, range(num), range(num))
    #fill in diagonal part
    P[0:n, 0:n] = identity_n
    for i in xrange(num_cycles+1):
        P[n:n+period, i*period:(i+1)*period] = identity_p
        P[i*period:(i+1)*period, n:n+period] = identity_p
    #now need to add the seasonlity sums to zero constraint
    for i in xrange(num_cycles+1):
        P[(i+1)*period-1,n:n+period] = -1.0
        P[n:n+period,(i+1)*period-1] = -1.0
    #remove the last row and column to eliminate the last periodic value as a free parameter
    return P[0:(n+period-1), 0:(n+period-1)]
    return P

def spmatrix2np(spmat):
    """
        Convert a matrix or spmatrix to numpy 2D array
    :param spmat: matrix or spmatrix
    :return: numpy 2D array of type float64
    """
    """
    :param spmat:
    :return:
    """
    return np.asarray(matrix(spmat))

def invert(spmat):
    arr = spmatrix2np(spmat)
    arr_inv = np.linalg.inv(arr)
    return sparse(matrix(arr_inv))




