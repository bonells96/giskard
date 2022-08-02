import pandas as pd

from generated.ml_worker_pb2 import SingleTestResult
from ml_worker.core.giskard_dataset import GiskardDataset
from ml_worker.core.model import GiskardModel
from ml_worker.testing.abstract_test_collection import AbstractTestCollection


class HeuristicTests(AbstractTestCollection):
    def test_right_label(self,
                         actual_slice: GiskardDataset,
                         model: GiskardModel,
                         classification_label: str,
                         threshold=0.5) -> SingleTestResult:
        """
        Summary: Test if the model returns the right classification label for a slice

        Description: The test is passed when the percentage of rows returning the right
        classification label is higher than the threshold in a given slice

        Example: For a credit scoring model, the test is passed when more than 50%
        of people with high-salaries are classified as “non default”

        Args:
           actual_slice(GiskardDataset):
              Slice of the  actual dataset
          model(GiskardModel):
              Model used to compute the test
          classification_label(str):
              Classification label you want to test
          threshold(float):
              Threshold for the percentage of passed rows

        Returns:
          actual_slices_size:
              Length of actual_slice tested
          metrics:
              The ratio of rows with the right classification label over the total of rows in the slice
          passed:
              TRUE if passed_ratio > threshold
          output_df:
              Dataframe containing the rows that do not return the right classification label
        """
        actual_slice.df.reset_index(drop=True, inplace=True)
        prediction_results = model.run_predict(actual_slice).prediction
        assert classification_label in model.classification_labels, \
            f'"{classification_label}" is not part of model labels: {",".join(model.classification_labels)}'

        passed_idx = actual_slice.df.loc[prediction_results == classification_label].index.values

        passed_ratio = len(passed_idx) / len(actual_slice)
        return self.save_results(SingleTestResult(
            actual_slices_size=[len(actual_slice)],
            metric=passed_ratio,
            passed=passed_ratio > threshold
        ))

    def test_output_in_range(self,
                             actual_slice: GiskardDataset,
                             model: GiskardModel,
                             classification_label=None,
                             min_range: float = 0.3,
                             max_range: float = 0.7,
                             threshold=0.5) -> SingleTestResult:
        """
        Summary: Test if the model output belongs to the right range for a slice

        Description: - The test is passed when the ratio of rows in the right range inside the
        slice is higher than the threshold.

         For classification: Test if the predicted probability for a given classification label
         belongs to the right range for a dataset slice

        For regression : Test if the predicted output belongs to the right range for a dataset slice

        Example :
        For Classification: For a credit scoring model, the test is passed when more than 50% of
        people with high wage have a probability of defaulting between 0 and 0.1

        For Regression : The predicted Sale Price of a house in the city falls in a particular range
        Args:
           actual_slice(GiskardDataset):
              Slice of the actual dataset
          model(GiskardModel):
              Model used to compute the test
          classification_label(str):
              Optional. Classification label you want to test
          min_range(float):
              Minimum probability of occurrence of classification label
          max_range(float):
              Maximum probability of occurrence of classification label
          threshold(float):
              Threshold for the percentage of passed rows

        Returns:
            slice_nb_rows:
                length of actual_slice tested

            metrics:
                the proportion of rows in the right range inside the slice
            passed:
                TRUE if metric > threshold
          output_df:
              For classification : Dataframe containing the rows with model classification probability that do not
              belong to the right range
              For Regression: Dataframe containing the rows with predicted output that do not belong to the right range


        """
        results_df = pd.DataFrame()
        actual_slice.df.reset_index(drop=True, inplace=True)

        prediction_results = model.run_predict(actual_slice)

        if model.model_type == "regression":
            results_df["output"] = prediction_results.raw_prediction

        elif model.model_type == "classification":
            assert classification_label in model.classification_labels, \
                f'"{classification_label}" is not part of model labels: {",".join(model.classification_labels)}'
            results_df["output"] = prediction_results.all_predictions[classification_label]

        else:
            raise ValueError(
                f"Prediction task is not supported: {model.model_type}"
            )

        passed_idx = actual_slice.df.loc[(results_df["output"] <= max_range) & (results_df["output"] >= min_range)].index.values

        passed_ratio = len(passed_idx) / len(actual_slice)

        return self.save_results(SingleTestResult(
            actual_slices_size=[len(actual_slice)],
            metric=passed_ratio,
            passed=passed_ratio >= threshold
        ))
