from abrox.core.abc_summary import ABCSummary
from abrox.core.config_check import ConfigTester
from abrox.core.abc_initializer import ABCInitializer
from abrox.core.rejection import ABCRejection
from abrox.core.plot import Plotter
from abrox.core.abc_preprocess import ABCPreProcessor
from abrox.core.abc_report import ABCReporter
from abrox.core.mcmc import MCMC


class Abc:
    """
    This is the class that organizes all steps required for
    a complete ABC analysis. The constructor calls the helper 
    class ConfigurationTester, which performs a sanity check on
    the config dictionary supplied by the user.
    """
    def __init__(self, config):
        self.config = config
        self._checkConfigSanity()

    def _checkConfigSanity(self):
        """Creates and runs an instance of the config sanity tester."""

        tester = ConfigTester(self.config)
        tester.checkForErrors()

    def run(self):
        """
        The only interface method of the class, responsible for handling
        all pre-processing and computation steps.
        """

        # Create an initializer instance, responsible for
        # importing/generating data, building the models,
        # and extracting relevant infos from config dict
        initializer = ABCInitializer(self.config)

        # 1. Initialize models according to parameters and return
        # a list with the models, and a list with the model names
        # 2. Get the data as a numpy array, or simulate, if no
        # data set specified to be imported
        # 3. Extract the relevant settings and hyperparameeters and
        # return them as a dictionary
        modelList, modelNames = initializer.buildAndGetModels()
        obsData = initializer.getOrGenerateObsData(modelList)
        settings = initializer.extractAndGetSettings()

        # Create a wrapper over the user-defined summary function
        # and obtain the summary statistics of the observed data
        summarizer = ABCSummary(self.config['summary'])
        sumStatObsData = summarizer.summarize(obsData)

        # Create an instance of the abc preprocessor, responsible for
        # generating an ABC reference table (a pandas DataFrame)
        # which contains four columns containing the following information:
        # Column 0: idx  - (the model index)
        # Column 1: param - a list of sampled parameters
        # Column 2: sumstat - a list of the summary statistics
        # Column 3: distance - the value obtained by evaluating the distance func
        pp = ABCPreProcessor(modelList, summarizer, sumStatObsData)

        # TODO -> parallel and jobs must also be specified in settings!
        refTable = pp.preprocess(settings['nsim'], parallel=True, jobs=4)

        # Create a rejecter instance, responsible for filtering
        # the reference table according to the specified number 'keep'
        # of rows to retain (retains those with smallest distance)
        rejecter = ABCRejection(refTable, settings['keep'])
        # TODO CAUTION: This should not always run!
        subset, threshold = rejecter.reject()

        # According to the specified algorithm, run the abc
        if settings['alg'] == "rejection":

            reporter = ABCReporter(subset, modelNames, settings['pnames'], settings['obj'])
            return reporter.report()

        if settings['alg'] == "mcmc":

            mcmc = MCMC(pp, subset, settings)

            samples, accepted = mcmc.run()

            plotter = Plotter(samples, settings['pnames'])
            plotter.plot()

            return samples
