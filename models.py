import numpy as np
import torch
from torch.nn import functional as F, Parameter
from torch.nn.init import xavier_normal_, xavier_uniform_


class HypER(torch.nn.Module):

    def __init__(self, d, d1, d2, **kwargs):

        super(HypER, self).__init__()
        self.in_channels = kwargs["in_channels"]
        self.out_channels = kwargs["out_channels"]
        self.filt_h = kwargs["filt_h"]
        self.filt_w = kwargs["filt_w"]

        self.E = torch.nn.Embedding(len(d.entities), d1, padding_idx=0)
        self.R = torch.nn.Embedding(len(d.relations), d2, padding_idx=0)
        self.inp_drop = torch.nn.Dropout(kwargs["input_dropout"])
        self.hidden_drop = torch.nn.Dropout(kwargs["hidden_dropout"])
        self.feature_map_drop = torch.nn.Dropout2d(kwargs["feature_map_dropout"])
        self.loss = torch.nn.BCELoss()

        self.bn0 = torch.nn.BatchNorm2d(self.in_channels)
        self.bn1 = torch.nn.BatchNorm2d(self.out_channels)
        self.bn2 = torch.nn.BatchNorm1d(d1)
        self.register_parameter('b', Parameter(torch.zeros(len(d.entities))))
        fc_length = (1 - self.filt_h + 1) * (d1 - self.filt_w + 1) * self.out_channels
        self.fc = torch.nn.Linear(fc_length, d1)
        fc1_length = self.in_channels * self.out_channels * self.filt_h * self.filt_w
        self.fc1 = torch.nn.Linear(d2, fc1_length)


    def init(self):

        xavier_normal_(self.E.weight.data)
        xavier_normal_(self.R.weight.data)


    def forward(self, e1_idx, r_idx):

        e1 = self.E(e1_idx).view(-1, 1, 1, self.E.weight.size(1))
        r = self.R(r_idx)
        x = self.bn0(e1)
        x = self.inp_drop(x)

        # Hpyer network
        k = self.fc1(r)
        k = k.view(-1, self.in_channels, self.out_channels, self.filt_h, self.filt_w)
        k = k.view(e1.size(0) * self.in_channels * self.out_channels, 1, self.filt_h, self.filt_w)

        x = x.permute(1, 0, 2, 3)

        x = F.conv2d(x, k, groups=e1.size(0))
        x = x.view(e1.size(0), 1, self.out_channels, 1 - self.filt_h + 1, e1.size(3) - self.filt_w + 1)
        x = x.permute(0, 3, 4, 1, 2)
        x = torch.sum(x, dim=3)
        x = x.permute(0, 3, 1, 2).contiguous()
        print('x convoluted:', x.size())

        x = self.bn1(x)
        x = self.feature_map_drop(x)
        x = x.view(e1.size(0), -1)
        x = self.fc(x)
        x = self.hidden_drop(x)
        x = self.bn2(x)
        x = F.relu(x)
        print('x nonlinearity:', x.size())

        # fully connected layer
        x = torch.mm(x, self.E.weight.transpose(1,0))
        print('x e2 dot product:', x.size())

        # bias
        x += self.b.expand_as(x)

        # prediction
        pred = F.sigmoid(x)

        return pred


class HypERPlus(torch.nn.Module):

    def __init__(self, d, d1, d2, **kwargs):

        super().__init__()

        self.in_channels = kwargs["in_channels"]
        self.out_channels = kwargs["out_channels"]
        self.filt_h = kwargs["filt_h"]
        self.filt_w = kwargs["filt_w"]

        self.E = torch.nn.Embedding(len(d.entities), d1, padding_idx=0)
        self.R = torch.nn.Embedding(len(d.relations), d2, padding_idx=0)

        self.inp_drop = torch.nn.Dropout(kwargs["input_dropout"])
        self.hidden_drop = torch.nn.Dropout(kwargs["hidden_dropout"])
        self.feature_map_drop = torch.nn.Dropout2d(kwargs["feature_map_dropout"])

        self.bn0 = torch.nn.BatchNorm2d(self.in_channels)
        self.bn1 = torch.nn.BatchNorm2d(self.out_channels)
        self.bn2 = torch.nn.BatchNorm1d(2 * d1)

        fc_length = (1 - self.filt_h + 1) * (2 * d1 - self.filt_w + 1) * self.out_channels
        self.fc = torch.nn.Linear(fc_length, 2 * d1)
        fc1_length = self.in_channels * self.out_channels * self.filt_h * self.filt_w
        self.fc1 = torch.nn.Linear(d2, fc1_length)
        self.fc2 = torch.nn.Linear(400, 1)
        # self.register_parameter('b', Parameter(torch.zeros(len(d.entities))))
        self.register_parameter('b', Parameter(torch.zeros(1)))

        self.loss = torch.nn.BCELoss()


    def init(self):

        xavier_normal_(self.E.weight.data)
        xavier_normal_(self.R.weight.data)


    def forward(self, e1_idx, r_idx, e2_idx):

        e1 = self.E(e1_idx).view(-1, 1, 1, self.E.weight.size(1))
        e2 = self.E(e2_idx).view(-1, 1, 1, self.E.weight.size(1))
        E = torch.cat((e1, e2), 3)

        print('e1:', e1.size())
        print('e2:', e2.size())
        print('E:', E.size())

        r = self.R(r_idx)
        x = self.bn0(E)
        x = self.inp_drop(x)

        # Hpyer network
        k = self.fc1(r)
        k = k.view(-1, self.in_channels, self.out_channels, self.filt_h, self.filt_w)
        k = k.view(E.size(0) * self.in_channels * self.out_channels, 1, self.filt_h, self.filt_w)

        x = x.permute(1, 0, 2, 3)

        # convolution
        x = F.conv2d(x, k, groups=E.size(0))
        x = x.view(E.size(0), 1, self.out_channels, 1 - self.filt_h + 1, E.size(3) - self.filt_w + 1)
        x = x.permute(0, 3, 4, 1, 2)
        x = torch.sum(x, dim=3)
        x = x.permute(0, 3, 1, 2).contiguous()

        # regularisation
        x = self.bn1(x)
        x = self.feature_map_drop(x)
        x = x.view(E.size(0), -1)
        x = self.fc(x)
        x = self.hidden_drop(x)
        x = self.bn2(x)
        print('x regularisation:', x.size())

        # fully connected layer commin up
        x = self.fc2(x)
        x = F.tanh(x)
        print('x Relu:', x.size())

        # bias
        x += self.b.expand_as(x)

        # # prediction
        # pred = F.sigmoid(x)
        pred = x

        return pred


class ConvE(torch.nn.Module):

    def __init__(self, d, d1, d2, **kwargs):

        super(ConvE, self).__init__()
        self.in_channels = kwargs["in_channels"]
        self.out_channels = kwargs["out_channels"]
        self.filt_h = kwargs["filt_h"]
        self.filt_w = kwargs["filt_w"]

        self.E = torch.nn.Embedding(len(d.entities), d1, padding_idx=0)
        self.R = torch.nn.Embedding(len(d.relations), d2, padding_idx=0)
        self.inp_drop = torch.nn.Dropout(kwargs["input_dropout"])
        self.hidden_drop = torch.nn.Dropout(kwargs["hidden_dropout"])
        self.feature_map_drop = torch.nn.Dropout2d(kwargs["feature_map_dropout"])
        self.loss = torch.nn.BCELoss()

        self.conv1 = torch.nn.Conv2d(self.in_channels, self.out_channels,
                            (self.filt_h, self.filt_w), 1, 0, bias=True)
        self.bn0 = torch.nn.BatchNorm2d(self.in_channels)
        self.bn1 = torch.nn.BatchNorm2d(self.out_channels)
        self.bn2 = torch.nn.BatchNorm1d(d1)
        self.register_parameter('b', Parameter(torch.zeros(len(d.entities))))
        fc_length = (20-self.filt_h+1)*(20-self.filt_w+1)*self.out_channels
        self.fc = torch.nn.Linear(fc_length, d1)

    def init(self):
        xavier_normal_(self.E.weight.data)
        xavier_normal_(self.R.weight.data)


    def forward(self, e1_idx, r_idx):
        e1 = self.E(e1_idx).view(-1, 1, 10, 20)
        r = self.R(r_idx).view(-1, 1, 10, 20)
        x = torch.cat([e1, r], 2)
        x = self.bn0(x)
        x= self.inp_drop(x)
        x= self.conv1(x)
        x= self.bn1(x)
        x= F.relu(x)
        x = self.feature_map_drop(x)
        x = x.view(e1.size(0), -1)
        x = self.fc(x)
        x = self.hidden_drop(x)
        x = self.bn2(x)
        x = F.relu(x)
        x = torch.mm(x, self.E.weight.transpose(1,0))
        x += self.b.expand_as(x)
        pred = F.sigmoid(x)
        return pred


class DistMult(torch.nn.Module):
    def __init__(self, d, d1, d2, **kwargs):
        super(DistMult, self).__init__()
        self.E = torch.nn.Embedding(len(d.entities), d1, padding_idx=0)
        self.R = torch.nn.Embedding(len(d.relations), d2, padding_idx=0)
        self.inp_drop = torch.nn.Dropout(kwargs["input_dropout"])
        self.loss = torch.nn.BCELoss()
        self.bn0 = torch.nn.BatchNorm1d(d1)

    def init(self):
        xavier_normal_(self.E.weight.data)
        xavier_normal_(self.R.weight.data)

    def forward(self, e1_idx, r_idx):
        e1 = self.E(e1_idx)
        r = self.R(r_idx)
        e1 = self.bn0(e1)
        e1 = self.inp_drop(e1)
        pred = torch.mm(e1*r, self.E.weight.transpose(1,0))
        pred = F.sigmoid(pred)
        return pred

class ComplEx(torch.nn.Module):
    def __init__(self, d, d1, d2, **kwargs):
        super(ComplEx, self).__init__()
        self.Er = torch.nn.Embedding(len(d.entities), d1, padding_idx=0)
        self.Rr = torch.nn.Embedding(len(d.relations), d2, padding_idx=0)
        self.Ei = torch.nn.Embedding(len(d.entities), d1, padding_idx=0)
        self.Ri = torch.nn.Embedding(len(d.relations), d2, padding_idx=0)
        self.inp_drop = torch.nn.Dropout(kwargs["input_dropout"])
        self.loss = torch.nn.BCELoss()
        self.bn0 = torch.nn.BatchNorm1d(d1)
        self.bn1 = torch.nn.BatchNorm1d(d1)

    def init(self):
        xavier_normal_(self.Er.weight.data)
        xavier_normal_(self.Rr.weight.data)
        xavier_normal_(self.Ei.weight.data)
        xavier_normal_(self.Ri.weight.data)

    def forward(self, e1_idx, r_idx):
        e1r = self.Er(e1_idx)
        rr = self.Rr(r_idx)
        e1i = self.Ei(e1_idx)
        ri = self.Ri(r_idx)
        e1r = self.bn0(e1r)
        e1r = self.inp_drop(e1r)
        e1i = self.bn1(e1i)
        e1i = self.inp_drop(e1i)
        pred = torch.mm(e1r*rr, self.Er.weight.transpose(1,0)) +\
               torch.mm(e1r*ri, self.Ei.weight.transpose(1,0)) +\
               torch.mm(e1i*rr, self.Ei.weight.transpose(1,0)) -\
               torch.mm(e1i*ri, self.Er.weight.transpose(1,0))
        pred = F.sigmoid(pred)
        return pred


class HypE(torch.nn.Module):

    def __init__(self, d, d1, d2, **kwargs):

        super(HypE, self).__init__()
        self.in_channels = kwargs["in_channels"]
        self.out_channels = kwargs["out_channels"]
        self.filt_h = kwargs["filt_h"]
        self.filt_w = kwargs["filt_w"]

        self.E = torch.nn.Embedding(len(d.entities), d1, padding_idx=0)
        r_dim = self.in_channels*self.out_channels*self.filt_h*self.filt_w
        self.R = torch.nn.Embedding(len(d.relations), r_dim, padding_idx=0)
        self.inp_drop = torch.nn.Dropout(kwargs["input_dropout"])
        self.hidden_drop = torch.nn.Dropout(kwargs["hidden_dropout"])
        self.feature_map_drop = torch.nn.Dropout2d(kwargs["feature_map_dropout"])
        self.loss = torch.nn.BCELoss()

        self.bn0 = torch.nn.BatchNorm2d(self.in_channels)
        self.bn1 = torch.nn.BatchNorm2d(self.out_channels)
        self.bn2 = torch.nn.BatchNorm1d(d1)
        self.register_parameter('b', Parameter(torch.zeros(len(d.entities))))
        fc_length = (10-self.filt_h+1)*(20-self.filt_w+1)*self.out_channels
        self.fc = torch.nn.Linear(fc_length, d1)


    def init(self):
        xavier_normal_(self.E.weight.data)
        xavier_normal_(self.R.weight.data)


    def forward(self, e1_idx, r_idx):

        e1 = self.E(e1_idx).view(-1, 1, 10, 20)

        r = self.R(r_idx)
        x = self.bn0(e1)
        x = self.inp_drop(x)

        k = r.view(-1, self.in_channels, self.out_channels, self.filt_h, self.filt_w)
        k = k.view(e1.size(0) * self.in_channels * self.out_channels, 1, self.filt_h, self.filt_w)

        x = x.permute(1, 0, 2, 3)

        x = F.conv2d(x, k, groups=e1.size(0))
        x = x.view(e1.size(0), 1, self.out_channels, 10-self.filt_h+1, 20-self.filt_w+1)
        x = x.permute(0, 3, 4, 1, 2)
        x = torch.sum(x, dim=3)
        x = x.permute(0, 3, 1, 2).contiguous()

        x = self.bn1(x)
        x = self.feature_map_drop(x)
        x = x.view(e1.size(0), -1)
        x = self.fc(x)
        x = self.hidden_drop(x)
        x = self.bn2(x)
        x = F.relu(x)
        x = torch.mm(x, self.E.weight.transpose(1,0))
        x += self.b.expand_as(x)
        pred = F.sigmoid(x)
        return pred


