__author__ = 'christina'

import numpy as np
import itertools, os
from collections import deque
from lib.persistance_module import env_vars, pred_vars
from lib.tiramola_logging import get_logger

class Predictor:
    def __init__(self):
        # 10 mins later (12 ticks per minute)
        self.projection_time = pred_vars['projection_time']
        self.use_sampling = pred_vars['use_sampling']
        self.sampling = pred_vars['sampling']
        self.measurements_file = env_vars['measurements_file']
        self.predictions_file = pred_vars['predictions_file']
        # measurements of latest minutes will be used in regression
        self.latest = pred_vars['use_latest_meas']
        self.degree = pred_vars['regression_degree']
        # store the current minute
        self.curr_min = self.latest

        #Create logger
        LOG_FILENAME = 'files/logs/Coordinator.log'
        self.log = get_logger('Predictor', 'INFO', logfile=LOG_FILENAME)

    '''
    Runs a polynomial regression on the latest measurements (in mins).
        :param degree, the degree of the polynomial you want to fit the data (use 1 for linear regression)
        :param latest, the number of mins you want to use for the regression
    '''
    def poly_regression(self):
        # mipws na ta diabazeis apo ti mnimi?
        # we log measurements every 5 sec, which means we have 12 measurements per minute
        stdin, stdout = os.popen2("tail -n " + str(12 * self.latest + 1) + " " + self.measurements_file)
        stdin.close()
        lines = stdout.readlines()
        stdout.close()
        prediction_file = open(self.predictions_file, 'a')
        # if os.stat(prediction_file).st_size == 0:
        #    prediction_file.write('Tick\t\tPredicted Lambda\n')
        # store past lambda's
        lambdas = []
        # set ticks, 1 tick per 5 sec...?
        ticks = []
        mins = 0.0
        samples = 12
        consider_lambda = True
        for line in lines:
            if self.use_sampling:
                if samples == 0:
                    samples = self.sampling
                    consider_lambda = True
                else:
                    consider_lambda = False
                    samples -= 1
            if consider_lambda:
                m = line.split('\t\t')  # state, lambda, throughput, latency, cpu, time tick, used

                lambdas.append(float(m[1]))
                ticks.append(mins)
            mins += float(env_vars['metric_fetch_interval']) / 60

        if len(lambdas) < self.latest - 1:
            self.log.info('# of mins considered %d, which is less than the %d measurements we need for a prediction' %
                          (len(lambdas), self.latest))
            return -1

        # fit lambdas in a polynomial
        coeff = np.polyfit(ticks, lambdas, deg=self.degree)  # coeff[0] = slope, coeff[1] = intercept
        # predict lambda in projection_time mins from now
        predicted_l = np.polyval(coeff, (self.mins + self.projection_time))
        # compute the current minute in the experiment
        self.curr_min += float(env_vars['decision_interval']) / 60
        prediction_file.write(str(self.curr_min) + '\t\t' +
                              str(self.curr_min + self.projection_time) + '\t\t' +
                              str(predicted_l) + '\n')

        prediction_file.close()

        return predicted_l

    def smoothing(self):
        return True

    def moving_average(self, iterable, n=3):
        # moving_average([40, 30, 50, 46, 39, 44]) --> 40.0 42.0 45.0 43.0
        # http://en.wikipedia.org/wiki/Moving_average
        it = iter(iterable)
        d = deque(itertools.islice(it, n - 1))
        d.appendleft(0)
        s = sum(d)
        for elem in it:
            s += elem - d.popleft()
            d.append(elem)
            yield s / float(n)

    def test_prediction(self):
        #training_file = env_vars["training_file"]
        test_file = 'files/measurements/test-pred-measurements/measurements.txt'
        # load training set
        meas = open(test_file, 'r+')
        #prediction_file = open(env_vars['predictions_file'], 'w')
        prediction_file = open('files/measurements/test-pred-measurements/predictions.txt', 'w')
        prediction_file.write('Tick\t\tPredicted Lambda\n')
        if os.stat(test_file).st_size != 0:
            # Read the training set measurements saved in the file.
            meas.next()  # Skip the first line with the headers of the columns
            # using latest num of measurements for regression
            latest = 5
            lambdas = []
            ticks = []
            mins = 0.0
            samples = 12
            consider_lambda = True
            for line in meas:
                # Skip comments (used in training sets)
                if not line.startswith('###'):
                    m = line.split('\t\t')

                    if self.use_sampling:
                        if samples == 0:
                            samples = self.sampling
                            consider_lambda = True
                        else:
                            consider_lambda = False
                            samples -= 1

                    if consider_lambda:
                        #print 'taking into consideration measurement at minute ' + str(mins)
                        # m[1] is lambda
                        lambdas.append(float(m[1]))
                        ticks.append(mins)
                        # if you have enough measurements, predict load in 10 mins,
                        # we collect measurements every 5 secs, which means we have 12 measurements per minute
                        if mins > latest:
                            coeff = np.polyfit(np.array(ticks[-latest:]), np.array(lambdas[-latest:]), deg=2)
                            # predict lambda in projection_time mins from now
                            predicted_l = np.polyval(coeff, (mins + self.projection_time))
                            prediction_file.write(str(mins + self.projection_time) + '\t\t' + str(predicted_l) + '\n')
                            print "Tick: " + str(mins) + " Predicted: " + str(predicted_l) + " lambda :" + str(m[1])

                    mins += float(env_vars['metric_fetch_interval']) / 60

        meas.close()

if __name__ == '__main__':
    pr = Predictor()
    pr.test_prediction()
