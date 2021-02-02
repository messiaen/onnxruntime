# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
# orttraining_test_ortmodule_api.py

import torch
from transformers import AutoConfig, BertForSequenceClassification
import pytest
import warnings
from unittest.mock import patch

import onnxruntime
from onnxruntime.training import _utils, ORTModule

# PyTorch model definitions for tests

class NeuralNetSinglePositionalArgument(torch.nn.Module):
    def __init__(self, input_size, hidden_size, num_classes):
        super(NeuralNetSinglePositionalArgument, self).__init__()

        self.fc1 = torch.nn.Linear(input_size, hidden_size)
        self.relu = torch.nn.ReLU()
        self.fc2 = torch.nn.Linear(hidden_size, num_classes)

    def forward(self, input1):
        out = self.fc1(input1)
        out = self.relu(out)
        out = self.fc2(out)
        return out

class NeuralNetMultiplePositionalArguments(torch.nn.Module):
    def __init__(self, input_size, hidden_size, num_classes):
        super(NeuralNetMultiplePositionalArguments, self).__init__()

        self.fc1 = torch.nn.Linear(input_size, hidden_size)
        self.relu = torch.nn.ReLU()
        self.fc2 = torch.nn.Linear(hidden_size, num_classes)

    def forward(self, input1, input2):
        model_input = input1 + input2
        out = self.fc1(model_input)
        out = self.relu(out)
        out = self.fc2(out)
        return out

class NeuralNetPositionalArguments(torch.nn.Module):
    def __init__(self, input_size, hidden_size, num_classes):
        super(NeuralNetPositionalArguments, self).__init__()

        self.fc1 = torch.nn.Linear(input_size, hidden_size)
        self.relu = torch.nn.ReLU()
        self.fc2 = torch.nn.Linear(hidden_size, num_classes)

    def forward(self, *model_inputs):
        model_input = torch.sum(torch.stack(model_inputs), dim=0)
        out = self.fc1(model_input)
        out = self.relu(out)
        out = self.fc2(out)
        return out

class NeuralNetKeywordArguments(torch.nn.Module):
    def __init__(self, input_size, hidden_size, num_classes):
        super(NeuralNetKeywordArguments, self).__init__()

        self.fc1 = torch.nn.Linear(input_size, hidden_size)
        self.relu = torch.nn.ReLU()
        self.fc2 = torch.nn.Linear(hidden_size, num_classes)

    def forward(self, x=None, y=None, z=None):
        model_input = torch.sum(torch.stack([x, y, z]), dim=0)
        out = self.fc1(model_input)
        out = self.relu(out)
        out = self.fc2(out)
        return out

class NeuralNetPositionalAndKeywordArguments(torch.nn.Module):
    def __init__(self, input_size, hidden_size, num_classes):
        super(NeuralNetPositionalAndKeywordArguments, self).__init__()

        self.fc1 = torch.nn.Linear(input_size, hidden_size)
        self.relu = torch.nn.ReLU()
        self.fc2 = torch.nn.Linear(hidden_size, num_classes)

    def forward(self, model_input, x=None, y=None, z=None):
        model_input = model_input + torch.sum(torch.stack([x, y, z]), dim=0)
        out = self.fc1(model_input)
        out = self.relu(out)
        out = self.fc2(out)
        return out

def _get_bert_for_sequence_classification_model(device):
    """Returns the BertForSequenceClassification pretrained model"""

    config = AutoConfig.from_pretrained(
            "bert-base-uncased",
            num_labels=2,
            num_hidden_layers=1,
            output_attentions = False,
            output_hidden_states = False,
    )

    model = BertForSequenceClassification.from_pretrained(
        "bert-base-uncased",
        config=config,
    ).to(device)

    return model

def _get_bert_for_sequence_classification_sample_data(device):
    """Returns sample data to be used with BertForSequenceClassification model"""

    input_ids = torch.randint(0, 100, (32, 64), dtype=torch.long, device=device)
    input_mask = torch.randint(0, 100, (32, 64), dtype=torch.long, device=device)
    labels = torch.randint(0, 1, (32,), dtype=torch.long, device=device)

    return input_ids, input_mask, labels

# ORTModule-API tests

def test_forward_call_single_positional_argument():
    device = 'cuda'

    N, D_in, H, D_out = 64, 784, 500, 10
    model = NeuralNetSinglePositionalArgument(D_in, H, D_out).to(device)
    model = ORTModule(model)
    x = torch.randn(N, D_in, device=device)
    try:
        model(x)
    except Exception as exception:
        raise exception

def test_forward_call_multiple_positional_arguments():
    device = 'cuda'

    N, D_in, H, D_out = 64, 784, 500, 10
    model = NeuralNetMultiplePositionalArguments(input_size=D_in, hidden_size=H, num_classes=D_out).to(device)
    model = ORTModule(model)
    x = torch.randn(N, D_in, device=device)
    y = torch.randn(N, D_in, device=device)
    try:
        model(x, y)
    except Exception as exception:
        raise exception

def test_forward_call_positional_arguments():
    device = 'cuda'

    N, D_in, H, D_out = 64, 784, 500, 10
    model = NeuralNetPositionalArguments(input_size=D_in, hidden_size=H, num_classes=D_out).to(device)
    model = ORTModule(model)
    args = [torch.randn(N, D_in, device=device), torch.randn(N, D_in, device=device), torch.randn(N, D_in, device=device)]
    try:
        model(*args)
    except Exception as exception:
        raise exception

def test_forward_call_keyword_arguments():
    device = 'cuda'

    N, D_in, H, D_out = 64, 784, 500, 10
    model = NeuralNetKeywordArguments(D_in, H, D_out).to(device)
    model = ORTModule(model)
    x = torch.randn(N, D_in, device=device)
    y = torch.randn(N, D_in, device=device)
    z = torch.randn(N, D_in, device=device)
    try:
        model(x, y, z)
    except Exception as exception:
        raise exception

def test_forward_call_positional_and_keyword_arguments():
    device = 'cuda'

    N, D_in, H, D_out = 64, 784, 500, 10
    model = NeuralNetPositionalAndKeywordArguments(D_in, H, D_out).to(device)
    model = ORTModule(model)
    a = torch.randn(N, D_in, device=device)
    x = torch.randn(N, D_in, device=device)
    y = torch.randn(N, D_in, device=device)
    z = torch.randn(N, D_in, device=device)
    try:
        model(a, x, y, z)
    except Exception as exception:
        raise exception

def test_model_cuda():
    original_device = 'cpu'
    to_device = 'cuda'

    N, D_in, H, D_out = 64, 784, 500, 10
    model = NeuralNetSinglePositionalArgument(D_in, H, D_out)
    model = ORTModule(model)
    x = torch.randn(N, D_in, device=to_device)
    for _, parameter_value in model.named_parameters():
        assert parameter_value.device.type == original_device

    model = model.cuda()
    model(x)

    for _, parameter_value in model.named_parameters():
        assert parameter_value.device.type == to_device

def test_model_cpu():
    original_device = 'cuda'
    to_device = 'cpu'

    N, D_in, H, D_out = 64, 784, 500, 10
    model = NeuralNetSinglePositionalArgument(D_in, H, D_out).to(original_device)
    model = ORTModule(model)
    x = torch.randn(N, D_in)
    for _, parameter_value in model.named_parameters():
        assert parameter_value.device.type == original_device

    model = model.cpu()
    model(x)

    for _, parameter_value in model.named_parameters():
        assert parameter_value.device.type == to_device

@pytest.mark.parametrize("original_device, to_argument, requires_export, device_type, device_index", [
    ('cpu', torch.device('cuda'), True, 'cuda', 0),
    ('cpu', 'cuda', True, 'cuda', 0),
    ('cpu', 'cuda:0', True, 'cuda', 0),
    ('cpu', 'cuda', True, 'cuda', 0),
    ('cuda', 'cuda', False, 'cuda', 0),
    ('cuda', 'cuda:0', False, 'cuda', 0),
    ('cuda', torch.device('cuda'), False, 'cuda', 0),
    ('cuda', 'cpu', True, 'cpu', 0),
    ('cuda', torch.device('cpu'), True, 'cpu', 0),
    ('cpu', 'cpu', False, 'cpu', None),
    ('cpu', torch.device('cpu'), False, 'cpu', None),
    ('cpu', torch.zeros(2, device=torch.device('cuda')), True, 'cuda', 0),
    ])
def test_model_to_device(original_device, to_argument, requires_export, device_type, device_index):
    N, D_in, H, D_out = 64, 784, 500, 10
    model = NeuralNetSinglePositionalArgument(D_in, H, D_out).to(original_device)
    model = ORTModule(model)
    x = torch.randn(N, D_in, device=device_type)
    for _, parameter_value in model.named_parameters():
        assert parameter_value.device.type == original_device

    model = model.to(to_argument)
    assert model._device_changed == requires_export
    assert model._device == torch.device(device_type+':'+str(device_index) if device_index is not None else device_type)
    model(x)

    for _, parameter_value in model.named_parameters():
        assert parameter_value.device.type == device_type

@pytest.mark.parametrize("original_device, to_device", [
    ('cuda', 'cpu'),
    ('cpu', 'cuda')
    ])
def test_model_to_device_and_back_to_original(original_device, to_device):
    N, D_in, H, D_out = 64, 784, 500, 10
    model = NeuralNetSinglePositionalArgument(D_in, H, D_out).to(original_device)
    model = ORTModule(model)
    for _, parameter_value in model.named_parameters():
        assert parameter_value.device.type == original_device

    model = model.to(to_device)
    assert model._device_changed == True
    assert model._device == torch.device(to_device+':0')

    for _, parameter_value in model.named_parameters():
        assert parameter_value.device.type == to_device

    model = model.to(original_device)
    assert model._device_changed == True
    assert model._device == torch.device(original_device+':0')
    for _, parameter_value in model.named_parameters():
        assert parameter_value.device.type == original_device

def test_model_with_different_devices_same_session():
    N, D_in, H, D_out = 64, 784, 500, 10
    model = NeuralNetSinglePositionalArgument(D_in, H, D_out)
    model = ORTModule(model)

    for i in range(5):
        if i % 2 == 0:
            device = 'cpu'
        else:
            device = 'cuda'

        model.to(device)
        x = torch.randn(N, D_in, device=device)
        y = model(x)

@pytest.mark.parametrize("device", ['cuda', 'cpu'])
def test_input_requires_grad_saved(device):
    N, D_in, H, D_out = 32, 784, 500, 10
    model = NeuralNetSinglePositionalArgument(D_in, H, D_out).to(device)
    model = ORTModule(model)
    x = torch.randn(N, D_in, device=device, requires_grad=True) + 1
    model(x)
    assert model._input_names_require_grad == ['input1']

@pytest.mark.parametrize("device", ['cuda', 'cpu'])
def test_input_requires_grad_backward_creates_input_grad(device):
    N, D_in, H, D_out = 32, 784, 500, 10
    model = NeuralNetSinglePositionalArgument(D_in, H, D_out).to(device)
    model = ORTModule(model)
    x = torch.randn(N, D_in, device=device, requires_grad=True)
    assert x.grad is None
    prediction = model(x)
    s = prediction.sum()
    s.backward()
    assert x.grad is not None

@pytest.mark.parametrize("device", ['cuda', 'cpu'])
def test_changes_input_requires_grad_reinitializes_module_gradient_graph_builder(device):
    N, D_in, H, D_out = 32, 784, 500, 10
    model = NeuralNetSinglePositionalArgument(D_in, H, D_out).to(device)
    model = ORTModule(model)
    x = torch.randn(N, D_in, device=device, requires_grad=True)
    model(x.data)
    module_gradient_graph_builder = model._module_gradient_graph_builder
    model(x)
    assert module_gradient_graph_builder != model._module_gradient_graph_builder

def test_gpu_reserved_memory_with_torch_no_grad():
    device = 'cuda'

    # Create a model and get the memory_reserved when torch.no_grad has been enabled
    # before and after export
    model_with_no_grad = _get_bert_for_sequence_classification_model(device)
    x, y, z = _get_bert_for_sequence_classification_sample_data(device)

    torch.cuda.empty_cache()
    model_with_no_grad = ORTModule(model_with_no_grad)
    mem_reserved_before_export = torch.cuda.memory_reserved(device)
    model_with_no_grad(x, y, None, None, None, None, z)
    mem_reserved_after_export_with_torch_no_grad = torch.cuda.memory_reserved(device)
    del model_with_no_grad
    torch.cuda.empty_cache()
    mem_reserved_after_cache_empty = torch.cuda.memory_reserved(device)
    assert mem_reserved_before_export == mem_reserved_after_cache_empty

    # Create another model and get the memory_reserved when torch.no_grad has not been enabled
    # after export
    model_without_no_grad = _get_bert_for_sequence_classification_model(device)
    model_without_no_grad = ORTModule(model_without_no_grad)
    mem_reserved_after_export_without_torch_no_grad = 0
    with patch('torch.no_grad'):
        model_without_no_grad(x, y, None, None, None, None, z)
        mem_reserved_after_export_without_torch_no_grad = torch.cuda.memory_reserved(device)

    assert mem_reserved_after_export_with_torch_no_grad < mem_reserved_after_export_without_torch_no_grad
    assert mem_reserved_before_export < mem_reserved_after_export_with_torch_no_grad

@pytest.mark.parametrize("device", ['cuda', 'cpu'])
def test_model_without_parameters(device):
    class Net(torch.nn.Module):
        def forward(self, x):
            return x

    model = Net().to(device)
    model = ORTModule(model).to(device)
    _ = model(torch.tensor(1.))


@pytest.mark.parametrize("device", ['cuda', 'cpu'])
def test_model_without_trainable_parameters(device):

    model = torch.nn.ReLU()
    model = ORTModule(model).to(device)

    batch_size = 5
    nb_classes = 2
    in_features = 10
    input = torch.randn(batch_size, in_features, device=device)
    target = torch.empty(batch_size, dtype=torch.long, device=device).random_(nb_classes)
    _ = model(input)

@pytest.mark.parametrize("device", ['cuda', 'cpu'])
def test_custom_model_without_trainable_parameters(device):
    class Net(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.fc1 = torch.nn.ReLU()

        def forward(self, x):
            return self.fc1(x)

    model = Net()
    model = ORTModule(model).to(device)
    model.to(device)
    _ = model(torch.tensor(1.).to(device))

@pytest.mark.parametrize("device", ['cuda', 'cpu'])
def test_model_with_unused_trainable_parameters(device):
    class Net(torch.nn.Module):
        def __init__(self, input_size, hidden_size, num_classes):
            super(Net, self).__init__()
            self.fc1 = torch.nn.Linear(input_size, hidden_size)
            self.relu = torch.nn.ReLU()
            self.fc2 = torch.nn.Linear(hidden_size, num_classes)

        def forward(self, input1):
            return input1

    model = Net(784, 500, 10)
    model = ORTModule(model).to(device)
    model(torch.tensor(1.).to(device))

def test_model_with_multiple_devices_cpu_cuda():
    class MultipleDeviceModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.fc1 = torch.nn.Linear(10, 10).cpu()
            self.fc2 = torch.nn.Linear(10, 10).cuda()

        def forward(self, x):
            x = self.fc1(x)
            x = self.fc2(x)
            return x

    model = MultipleDeviceModel()
    with pytest.raises(RuntimeError) as e:
        model = ORTModule(model)
    assert str(e.value) == 'ORTModule supports a single device per model for now'

def test_model_with_multiple_devices_to_to():
    class MultipleDeviceModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.fc1 = torch.nn.Linear(10, 10).to('cpu')
            self.fc2 = torch.nn.Linear(10, 10).to('cuda')

        def forward(self, x):
            x = self.fc1(x)
            x = self.fc2(x)
            return x

    model = MultipleDeviceModel()
    with pytest.raises(RuntimeError) as e:
        model = ORTModule(model)
    assert str(e.value) == 'ORTModule supports a single device per model for now'

def test_model_with_multiple_devices_to_cpu():
    class MultipleDeviceModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.fc1 = torch.nn.Linear(10, 10).to('cuda')
            self.fc2 = torch.nn.Linear(10, 10).cpu()

        def forward(self, x):
            x = self.fc1(x)
            x = self.fc2(x)
            return x

    model = MultipleDeviceModel()
    with pytest.raises(RuntimeError) as e:
        model = ORTModule(model)
    assert str(e.value) == 'ORTModule supports a single device per model for now'

def test_model_with_multiple_devices_to_cuda():
    class MultipleDeviceModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.fc1 = torch.nn.Linear(10, 10).to('cpu')
            self.fc2 = torch.nn.Linear(10, 10).cuda()

        def forward(self, x):
            x = self.fc1(x)
            x = self.fc2(x)
            return x

    model = MultipleDeviceModel()
    with pytest.raises(RuntimeError) as e:
        model = ORTModule(model)
    assert str(e.value) == 'ORTModule supports a single device per model for now'

@pytest.mark.parametrize("device", ['cuda', 'cuda:0', 'cuda:1', 'cuda:2'])
def test_model_with_different_cuda_devices(device):

    # Trick to run this test in single GPU machines
    device_id = _utils.get_device_index(device)
    if device_id >= torch.cuda.device_count():
        warnings.warn('Skipping test_model_with_different_cuda_devices(cuda:{})'.format(device_id))
        return

    N, D_in, H, D_out = 64, 784, 500, 10
    model = NeuralNetSinglePositionalArgument(D_in, H, D_out).to(device)
    model = ORTModule(model)
    model.to(device)
    x = torch.randn(N, D_in, device=device)
    model(x)
