import torch
import torch.nn as nn
from types import MethodType


def orthogonalize(M):
    # six step Newton-Schulz by @YouJiacheng
    # coefficients from: https://twitter.com/YouJiacheng/status/1893704552689303901
    # found by optimization: https://gist.github.com/YouJiacheng/393c90cbdc23b09d5688815ba382288b/5bff1f7781cf7d062a155eecd2f13075756482ae
    # the idea of stability loss was from @leloykun

    abc_list = [
        (3955 / 1024, -8306 / 1024, 5008 / 1024), (3735 / 1024, -6681 / 1024, 3463 / 1024),
        (3799 / 1024, -6499 / 1024, 3211 / 1024), (4019 / 1024, -6385 / 1024, 2906 / 1024),
        (2677 / 1024, -3029 / 1024, 1162 / 1024), (2172 / 1024, -1833 / 1024, 682 / 1024)
    ]

    transpose = M.shape[1] > M.shape[0]
    if transpose:
        M = M.T
    M = M / torch.linalg.norm(M)
    for a, b, c in abc_list:
        A = M.T @ M
        I = torch.eye(A.shape[0], device=M.device, dtype=M.dtype)
        M = M @ (a * I + b * A + c * A @ A)
    if transpose:
        M = M.T
    return M


class GeLU(nn.GELU):
    def __init__(self):
        super().__init__(approximate='tanh')

    def forward(self, x):
        return super().forward(x) / 1.1289  # 1.1289 is the max derivative of gelu(x)


activation_map = {
    # 1-Lipschitz activateion
    'relu': nn.ReLU,
    'elu': nn.ELU,
    'gelu': GeLU,
}


def hook_modnorm(mlp):
    # Assume: `mlp` is nn.Sequential, constructed by ONLY bias-free linear and 1-Lipschitz activation
    #
    assert isinstance(mlp, nn.Sequential)
    num_linear = 0
    num_activation = 0
    for layer in mlp:
        # assert isinstance(layer, nn.Linear) or type(layer) in activation_map.values()
        # assert layer.bias is None
        if isinstance(layer, nn.Linear):
            assert layer.bias is None
            num_linear += 1
        elif type(layer) in activation_map.values():
            num_activation += 1
        else:
            raise ValueError(f"Unsupported layer type: {type(layer)}")

    # Build hook in Linear Layer and Sequential Layer:
    #    # Init with target norm, and add project & dualize methods.

    def _linear_initialize_weights(self):
        with torch.no_grad():
            weight = torch.randn(self.out_features, self.in_features)
            weight = orthogonalize(weight) * torch.sqrt(torch.tensor(self.out_features / self.in_features))
            self.weight.copy_(weight)

    def _linear_project_weights(self):
        """Project weights to the constraint manifold"""
        with torch.no_grad():
            weight = orthogonalize(self.weight) * torch.sqrt(torch.tensor(self.out_features / self.in_features))
            self.weight.copy_(weight)

    def _linear_dualize_gradients(self):
        """Apply dualization to gradients"""
        if self.weight.grad is not None:
            with torch.no_grad():
                grad = self.weight.grad
                d_weight = orthogonalize(grad) * torch.sqrt(
                    torch.tensor(self.out_features / self.in_features)
                ) * self.target_norm
                self.weight.grad.copy_(d_weight)

    def _sequential_project_weights(self):
        """Project weights to the constraint manifold"""
        for layer in self:
            if isinstance(layer, nn.Linear):
                layer.project_weights()

    def _sequential_dualize_gradients(self):
        """Apply dualization to gradients"""
        for layer in self:
            if isinstance(layer, nn.Linear):
                layer.dualize_gradients()

    for layer in mlp:
        if isinstance(layer, nn.Linear):
            layer.register_buffer('target_norm', torch.tensor(1.0 / num_linear, dtype=torch.float))
            layer.project_weights = MethodType(_linear_project_weights, layer)  # type:ignore
            layer.dualize_gradients = MethodType(_linear_dualize_gradients, layer)  # type:ignore
            _linear_initialize_weights(layer)  # type:ignore
    mlp.project_weights = MethodType(_sequential_project_weights, mlp)  # type:ignore
    mlp.dualize_gradients = MethodType(_sequential_dualize_gradients, mlp)  # type:ignore

    return mlp
    ...


def build_mnmlp(input_dim, hidden_dims, output_dim, activation):
    activation = activation_map[activation]()

    actor_layers = []
    actor_layers.append(nn.Linear(input_dim, hidden_dims[0], bias=False))
    actor_layers.append(activation)
    for layer_index in range(len(hidden_dims)):
        if layer_index == len(hidden_dims) - 1:
            actor_layers.append(nn.Linear(hidden_dims[layer_index], output_dim, bias=False))
        else:
            actor_layers.append(nn.Linear(hidden_dims[layer_index], hidden_dims[layer_index + 1], bias=False))
            actor_layers.append(activation)
    mlp = nn.Sequential(*actor_layers)
    hook_modnorm(mlp)
    return mlp
    ...


def main():
    mlp = build_mnmlp(10, [100, 300, 200], 20, 'elu')
    print(mlp)
    print(mlp(torch.randn(10, 10)).shape)
    mlp.project_weights()
    mlp.dualize_gradients()


if __name__ == "__main__":
    (main)()
