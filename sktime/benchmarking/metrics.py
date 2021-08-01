# -*- coding: utf-8 -*-
__all__ = ["PairwiseMetric", "AggregateMetric"]
__author__ = ["Viktor Kazakov", "Markus Löning"]

import numpy as np

from sktime.benchmarking.base import BaseMetric


class PairwiseMetric(BaseMetric):
    def __init__(self, func, name=None, **kwargs):
        name = func.__name__ if name is None else name
        self.func = func
        super(PairwiseMetric, self).__init__(name=name, **kwargs)

    def compute(self, y_true, y_pred):
        # compute mean
        mean = self.func(y_true, y_pred)

        # compute stderr based on pairwise metrics
        n_instances = len(y_true)
        pointwise_metrics = np.array(
            [self.func([y_true[i]], [y_pred[i]]) for i in range(n_instances)]
        )
        stderr = np.std(pointwise_metrics) / np.sqrt(
            n_instances - 1
        )  # sample standard error of the mean

        return mean, stderr


class AggregateMetric(BaseMetric):
    def __init__(self, func, method="jackknife", name=None, **kwargs):
        allowed_methods = ("jackknife",)
        if method not in allowed_methods:
            raise NotImplementedError(
                f"Provided method is not implemented yet. "
                f"Currently only: {allowed_methods} are implemented"
            )
        self.method = method

        name = func.__name__ if name is None else name
        self.func = func

        super(AggregateMetric, self).__init__(name=name, **kwargs)

    def compute(self, y_true, y_pred):
        """Compute metric and standard error

        References
        ----------
        .. [1] Efron and Stein, (1981), "The jackknife estimate of variance."

        .. [2] McIntosh, Avery. "The Jackknife Estimation Method".
            <http://people.bu.edu/aimcinto/jackknife.pdf>

        .. [3] Efron, Bradley. "The Jackknife, the Bootstrap, and other
            Resampling Plans". Technical Report No. 63, Division of
            Biostatistics,
            Stanford University, December, 1980.

        .. [4] Jackknife resampling
        <https://en.wikipedia.org/wiki/Jackknife_resampling>
        """
        # compute aggregate metric
        mean = self.func(y_true, y_pred, **self.kwargs)

        # compute stderr based on jackknifed metrics
        n_instances = len(y_true)
        index = np.arange(n_instances)

        # get jackknife samples of index
        jack_idx = self._jackknife_resampling(index)

        # compute metrics on jackknife samples
        jack_pointwise_metric = np.array(
            [self.func(y_true[idx], y_pred[idx], **self.kwargs) for idx in jack_idx]
        )

        # compute standard error over jackknifed metrics
        jack_stderr = self._compute_jackknife_stderr(jack_pointwise_metric)
        return mean, jack_stderr

    @staticmethod
    def _compute_jackknife_stderr(x):
        """Compute standard error of jacknife samples

        References
        ----------
        .. [1] Efron and Stein, (1981), "The jackknife estimate of variance.
        """
        n_instances = x.shape[0]
        # np.sqrt((((n - 1) / n) * np.sum((x - x.mean()) ** 2)))
        return np.sqrt(n_instances - 1) * np.std(x)

    @staticmethod
    def _jackknife_resampling(x):
        """Performs jackknife resampling on numpy arrays.

        Jackknife resampling is a technique to generate 'n' deterministic
        samples
        of size 'n-1' from a measured sample of size 'n'. Basically, the i-th
        sample, (1<=i<=n), is generated by means of removing the i-th
        measurement
        of the original sample. Like the bootstrap resampling, this statistical
        technique finds applications in estimating variance, bias,
        and confidence
        intervals.

        Parameters
        ----------
        x : numpy.ndarray
            Original sample (1-D array) from which the jackknife resamples
            will be
            generated.

        Returns
        -------
        resamples : numpy.ndarray
            The i-th row is the i-th jackknife sample, i.e., the original
            sample
            with the i-th measurement deleted.

        References
        ----------
        .. [1] modified version of
        http://docs.astropy.org/en/stable/_modules/astropy/stats/jackknife.html
        """
        n_instances = x.shape[0]

        # preallocate array
        dtype = x.dtype
        resamples = np.empty([n_instances, n_instances - 1], dtype=dtype)

        # jackknife resampling
        for i in range(n_instances):
            resamples[i] = np.delete(x, i)

        return resamples
