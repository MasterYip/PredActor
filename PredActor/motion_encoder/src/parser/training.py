import os

from .base import add_misc_options, add_cuda_options, adding_cuda, ArgumentParser
from .tools import save_args
from .dataset import add_dataset_options
from .model import add_model_options, parse_modelname
from .checkpoint import construct_checkpointname


def add_training_options(parser):
    group = parser.add_argument_group('Training options')
    group.add_argument("--batch_size", type=int, required=True, help="size of the batches")
    group.add_argument("--num_epochs", type=int, required=True, help="number of epochs of training")
    group.add_argument("--lr", type=float, required=True, help="AdamW: learning rate")
    group.add_argument("--snapshot", type=int, required=True, help="frequency of saving model/viz")
    group.add_argument("--num_workers", type=int, default=16, help="data loader workers")
    group.add_argument("--max_steps", type=int, default=0, help="stop after this many optimizer steps; zero is unlimited")
    group.add_argument("--init_checkpoint", help="initialize all model weights, including learned CLIP; starts a new optimizer")
    

def parser():
    parser = ArgumentParser()

    # misc options
    add_misc_options(parser)

    # cuda options
    add_cuda_options(parser)
    
    # training options
    add_training_options(parser)

    # dataset options
    add_dataset_options(parser)

    # model options
    add_model_options(parser)

    opt = parser.parse_args()
    if min(opt.batch_size, opt.num_epochs, opt.snapshot) < 1 or opt.lr <= 0:
        parser.error("batch_size, num_epochs, snapshot and lr must be positive")
    if opt.num_workers < 0 or opt.max_steps < 0:
        parser.error("num_workers and max_steps must be nonnegative")
    
    # remove None params, and create a dictionnary
    parameters = {key: val for key, val in vars(opt).items() if val is not None}

    # parse modelname
    ret = parse_modelname(parameters["modelname"])
    parameters["modeltype"], parameters["archiname"], parameters["losses"] = ret
    
    # update lambdas params
    lambdas = {}
    for loss in parameters["losses"]:
        lambdas[loss] = opt.__getattribute__(f"lambda_{loss}")
    parameters["lambdas"] = lambdas

    clip_lambdas = {'image':{}, 'text':{}}
    for d in clip_lambdas.keys():
        losses_name = f'clip_{d}_losses'
        parameters[losses_name] = parameters[losses_name].split('_') if parameters[losses_name] != '' else []
        for loss in parameters[losses_name]:
            clip_lambdas[d][loss] = opt.__getattribute__(f"clip_lambda_{loss}")
            clip_lambdas[d][loss] = opt.__getattribute__(f"clip_lambda_{loss}")
    parameters["clip_lambdas"] = clip_lambdas

    if "folder" not in parameters:
        parameters["folder"] = construct_checkpointname(parameters, parameters["expname"])

    os.makedirs(parameters["folder"], exist_ok=True)
    save_args(parameters, folder=parameters["folder"])

    adding_cuda(parameters)
    
    return parameters
