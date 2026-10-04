"""Optional independent sampling for training normalizers."""


def fit_training_normalizer(dataset, dataset_config):
    kwargs = {"data_sample_rate": dataset_config.get("data_sample_rate", 0.05)}
    seed = dataset_config.get("normalizer_sampling_seed")
    if seed is not None:
        kwargs["sampling_seed"] = int(seed)
    return dataset.get_normalizer(**kwargs)
