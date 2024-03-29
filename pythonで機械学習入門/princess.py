import numpy as np
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import chainer.optimizers as Opt
import chainer.functions as F
import chainer.links as L
from chainer import Variable,Chain,config,cuda

import chainer
import chainer.datasets as ds
import chainer.dataset.convert as con
from chainer.iterators import SerialIterator as siter
from chainer import optimizer_hooks as oph
from IPython import display
from tqdm import tqdm

def data_divide(Dtrain,D,xdata,tdata):
    index = np.random.permutation(range(D))
    xtrain = xdata[index[0:Dtrain],:]
    ttrain = tdata[index[0:Dtrain]]
    xtest = xdata[index[Dtrain:D],:]
    ttest = tdata[index[Dtrain:D]]
    return xtrain,xtest,ttrain,ttest

def plot_result(result1,title,xlabel,ylabel,ymin=0.0,ymax=1.0):
    Tall = len(result1)
    plt.plot(range(Tall),result1)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xlim([0,Tall])
    plt.ylim([ymin,ymax])
    plt.show()

def plot_result2(result1,result2,title,xlabel,ylabel,ymin=0.0,ymax=1.0):
    Tall = len(result1)
    plt.plot(range(Tall),result1)
    plt.plot(range(Tall),result2)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xlim([0,Tall])
    plt.ylim([ymin,ymax])
    plt.show()

def plot_result3(result1,epoch,filename,title,xlabel,ylabel,ymin=0.0,ymax=1.0):
    Tall = len(result1)
    plt.plot(range(Tall),result1)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xlim([0,Tall])
    plt.ylim([ymin,ymax])
    plt.savefig(filename+"_{0:03d}res3.png".format(epoch))
    plt.show()

def plot_result4(result1,result2,epoch,filename,title,xlabel,ylabel,ymin=0.0,ymax=1.0):
    Tall = len(result1)
    plt.close() 
    plt.plot(range(Tall),result1)
    plt.plot(range(Tall),result2)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xlim([0,Tall])
    plt.ylim([ymin,ymax])
    plt.savefig(filename+"_{0:03d}res4.png".format(epoch))
    plt.show()

def learning_regression(model,optNN,data,result,T=10):
    for time in tqdm(range(T)):
        config.train = True
        optNN.target.cleargrads()
        ytrain=model(data[0])
        loss_train= F.mean_squared_error(ytrain,data[2])
        loss_train.backward()
        optNN.update()
        
    config.train = False
    ytest = model(data[1])
    loss_test=F.mean_squared_error(ytest,data[3])
    result[0].append(cuda.to_cpu(loss_train.data))
    result[1].append(cuda.to_cpu(loss_test.data))
    
    
def learning_classification(model,optNN,data,result,T=10):
    for time in tqdm(range(T)):
        config.train = True
        optNN.target.cleargrads()
        ytrain=model(data[0])
        loss_train= F.softmax_cross_entropy(ytrain,data[2])
        acc_train = F.accuracy(ytrain,data[2])
        loss_train.backward()
        optNN.update()
   
    config.train = False
    ytest = model(data[1])
    loss_test=F.softmax_cross_entropy(ytest,data[3])
    acc_test=F.accuracy(ytest,data[3])
    result[0].append(cuda.to_cpu(loss_train.data))
    result[1].append(cuda.to_cpu(loss_test.data))
    result[2].append(cuda.to_cpu(acc_train.data))
    result[3].append(cuda.to_cpu(acc_test.data))        

class CNN(Chain):
    def __init__(self,ch_in,ch_out,ksize=4,stride=2,pad=1,pooling=True):
        self.pooling = pooling
        layers = {}
        layers['conv1']=L.Convolution2D(ch_in,ch_out,ksize=ksize,stride=stride,pad=pad)
        layers['bnorm1']=L.BatchNormalization(ch_out)
        super().__init__(**layers)
    
    def __call__(self,x,ksize=3,stride=2,pad=1):
        h=self.conv1(x)
        h=F.relu(h)
        h=self.bnorm1(h)
        if self.pooling == True:
            h=F.max_pooling_2d(h,ksize=ksize,stride=stride,pad=pad)
        return h           

def flip_labeled(labeled_data):
	data,label=labeled_data

	z=np.random.randint(2)
	if z ==1:
		data=data[:,::-1,:]

	z=np.random.randint(2)
	if z ==1:
		data=data[:,:,::-1]

	z=np.random.randint(2)
	if z ==1:
		data=data.transpose(0,2,1)

	return data,label

def shift_labeled(labeled_data):
	data,label=labeled_data

	ch,Ny,Nx=data.shape
	z_h=Ny*(2.0*np.random.rand(1)-1.0)*0.2
	z_v=Nx*(2.0*np.random.rand(1)-1.0)*0.2
	data=np.roll(data,int(z_h),axis=1)
	data=np.roll(data,int(z_v),axis=2)

	return data,label

class ResBlock(Chain):
	def  __init__(self,ch,bn=True):
		self.bn=bn
		layers = {}
		layers["conv1"]=L.Convolution2D(ch,ch,3,1,1)
		layers["conv2"]=L.Convolution2D(ch,ch,3,1,1)
		layers["bnorm1"]=L.BatchNormalization(ch)
		layers["bnorm2"]=L.BatchNormalization(ch)
		super(). __init__(**layers)

	def  __call__(self,x):
		h = self.conv1(x)
		if self.bn == True:
			h=self.bnorm1(h)
		h = F.relu(h)
		h=self.conv2(h)
		if self.bn==True:
			h=self.bnorm2(h)
		h=h+x #残留学習
		h=F.relu(h)
		return h

def check_network(x,link):
	print("input:",x.shape)
	h=link(x)
	print("output:",h.shape)
	return h

class Bottleneck(Chain):
	def __init__(self, ch, bn=True):
		self.bn=bn
		layers={}
		layers["conv1"]=L.Convolution2D(ch,ch,ksize=1,stride=1,pad=0)
		layers["conv2"]=L.Convolution2D(ch,ch,ksize=1,stride=3,pad=0)
		layers["conv3"]=L.Convolution2D(ch,ch,ksize=1,stride=1,pad=0)
		layers["bnorm1"]=L.BatchNormalization(ch)
		layers["bnorm2"]=L.BatchNormalization(ch)
		layers["bnorm3"]=L.BatchNormalization(ch)
		super().__init__(**layers)
	
	def __call__(self,x):
		h=self.conv1(x)
		if self.bn==True:
			h=self.bnorm1(h)
		h=F.relu(h)
		h=self.conv2(h)
		if self.bn==True:
			h=self.bnorm2(h)
		h=F.relu(h)
		h=self.conv3(h)
		if self.bn==True:
			h=self.bnorm3(h)
		h=h+x
		h=F.relu(h)

		return h

class PixelShuffler(Chain):
	def __init__(self,ch,r=2):
		self.r=r
		self.ch=ch
		super().__init__()

	def __call__(self,x):
		batchsize,ch,Ny,Nx=x.shape
		ch_y=ch//(self.r**2)
		Ny_y=Ny*self.r
		Nx_y=Nx*self.r
		h=F.reshape(x,(batchsize,self.r,self.r,ch_y,Ny,Nx))
		h=F.transpose(h,(0,3,4,1,5,2))
		y=F.reshape(h,(batchsize,ch_y,Ny_y,Nx_y))
		return y

class CBR(Chain):
	def __init__(self,ch_in, ch_out, sample='down',bn=True, act=F.relu,drop=False):
		self.bn=bn
		self.act=act
		self.drop=drop

		layers={}
		if sample=="down":
			layers["conv"]=L.Convolution2D(ch_in,ch_out,4,2,1)
		elif sample=="up":
			layers["conv"]=L.Deconvolution2D(ch_in,ch_out,4,2,1)
		if bn:
			layers["bnorm"]=L.BatchNormalization(ch_out)
		super().__init__(**layers)

	def __call__(self,x):
		h=self.conv(x)
		
		if self.bn==True:
			h=self.bnorm(h)
		if self.drop==True:
			h=F.dropout(h)
		h=self.act(h)
		return h

import os

def add_labeled_data(folder,i,all_list):
	image_files=os.listdir(folder)
	for k in range(len(image_files)):
		labeled_file=(folder+"/"+image_files[k],i)
		all_list.append(labeled_file)
	return all_list

import PIL.Image as im
def labeled64(labeled_data):
	data,label=labeled_data
	data=data.astype(np.uint8)
	data=im.fromarray(data.transpose(1,2,0))
	data=data.resize((64,64),im.BICUBIC)
	data=np.asarray(data).transpose(2,0,1)
	data=data.astype(np.float32)/255
	return data,label

def temp_image(epoch,filename,xtest,ztest,gen,dis,Nfig=3):
	print("epoch",epoch)
	with chainer.using_config("train",False),chainer.using_config("enable_backprop",False):
		ytest=gen(ztest)
		score_true=dis(xtest)
		score_false=dis(ytest)
	plt.figure(figsize=(12,12))
	for k in range(Nfig):
		plt.subplot(1,Nfig,k+1)
		plt.title("{}".format(score_true[k].data))
		plt.axis("off")
		plt.imshow(cuda.to_cpu(xtest[k,:,:,:]).transpose(1,2,0))
	#plt.show()
	plt.figure(figsize=(12,12))
	for k in range(Nfig):
		plt.subplot(1,Nfig,k+1)
		plt.title("{}".format(score_false[k].data))
		plt.axis("off")
		plt.imshow(cuda.to_cpu(ytest[k,:,:,:].data).transpose(1,2,0))
	plt.savefig(filename+"_{0:03d}.png".format(epoch))
	plt.show()


def learning_GAN(gen,dis,optgen,optdis,data,result,T=1):
    for time in range(T):
        optgen.target.cleargrads()
        ytemp=gen(data[1])
        with chainer.using_config("train",False):
            ytrain_false=dis(ytemp)
        #loss_train_gen=0.5*F.mean((ytrain_false-1.0)**2)
        loss_train_gen=0.5*F.mean(F.softplus(-ytrain_false))
        loss_train_gen.backward()
        optgen.update()

        optdis.target.cleargrads()
        ytrain_false=dis(ytemp.data)
        ytrain_true=dis(data[0])
        #loss1=0.5*F.mean((ytrain_false)**2,axis=(0,1))
        #loss2=0.5*F.mean((ytrain_true-1.0)**2)
        loss1=0.5*F.mean(F.softplus(ytrain_false))
        loss2=0.5*F.mean(F.softplus(-ytrain_true))
        loss_train_dis=loss1+loss2
        loss_train_dis.backward()
        optdis.update()
    result[0].append(cuda.to_cpu(loss_train_gen.data))
    result[1].append(cuda.to_cpu(loss1.data))
    result[2].append(cuda.to_cpu(loss2.data))
    
import chainer.serializers as ser

def save_model(NN,filename):
	NN.to_cpu()
	ser.save_hdf5(filename,NN,compression=4)
	NN.to_gpu()

def load_model(NN,filename):
	ser.load_hdf5(filename,NN)
	NN.to_gpu()

def learning_L1(gen_BtoA,gen_AtoB,optgen_BtoA,optgen_AtoB,data,T=5):
    a=10
    for time in range(T):
        optgen_BtoA.target.cleargrads()
        optgen_AtoB.target.cleargrads()
        ytemp1=gen_BtoA(data[0])
        ytrain1=gen_AtoB(ytemp1)
        ytemp2=gen_AtoB(data[1])
        ytrain2=gen_BtoA(ytemp2)
        loss_train=0.5*a*F.mean_absolute_error(ytrain1,data[0])+0.5*a*F.mean_absolute_error(ytrain2,data[1])
        loss_train.backward()
        result=loss_train.data
        optgen_BtoA.update()
        optgen_AtoB.update()

def learning_consist(gen_BtoA,gen_AtoB,optgen_BtoA,optgen_AtoB,data,T=5):
    a=10
    for time in range(T):
        optgen_BtoA.target.cleargrads()
        optgen_AtoB.target.cleargrads()
        ytemp1=gen_BtoA(data[1])
        ytemp2=gen_AtoB(data[0])
        loss_train=0.5*a*F.mean_absolute_error(ytemp1,data[1])+0.5*a*F.mean_absolute_error(ytemp2,data[0])
        loss_train.backward()
        result=loss_train.data
        optgen_BtoA.update()
        optgen_AtoB.update()
        

def temp_image2(epoch,filename,dataA,dataB,gen_AtoB,gen_BtoA,dis_A,dis_B):
    print("epoch",epoch)
    with chainer.using_config("train",False),chainer.using_config("enable_backprop",False):
        xtestAB=gen_AtoB(cuda.to_gpu(dataA))
        scoreAB=dis_B(xtestAB)
        xtestABA=gen_BtoA(xtestAB)
        xtestBA=gen_BtoA(cuda.to_gpu(dataB))
        scoreBA=dis_A(xtestBA)
        xtestBAB=gen_AtoB(xtestBA)
    kA=np.random.randint(len(dataA))
    kB=np.random.randint(len(dataB))
    plt.figure(figsize=(12,9))
    plt.subplot(3,2,1)
    plt.axis("off")
    plt.title("imageA")
    plt.imshow(dataA[kA,:,:,:].transpose(1,2,0))
    plt.subplot(3,2,2)
    plt.axis("off")
    plt.imshow(dataB[kB,:,:,:].transpose(1,2,0))
    plt.axis("off")
    plt.title("imageB")
    plt.subplot(3,2,3)
    plt.axis("off")
    plt.title("{}".format(cuda.to_cpu(scoreAB[kA].data)))
    plt.imshow(cuda.to_cpu(xtestAB[kA,:,:,:].data).transpose(1,2,0))
    plt.subplot(3,2,4)
    plt.axis("off")
    plt.title("{}".format(cuda.to_cpu(scoreBA[kB].data)))
    plt.imshow(cuda.to_cpu(xtestBA[kB,:,:,:].data).transpose(1,2,0))
    plt.subplot(3,2,5)
    plt.axis("off")
    plt.title("A to B to A")
    plt.imshow(cuda.to_cpu(xtestABA[kA,:,:,:].data).transpose(1,2,0))
    plt.subplot(3,2,6)
    plt.axis("off")
    plt.title("B to A to B")
    plt.imshow(cuda.to_cpu(xtestBAB[kB,:,:,:].data).transpose(1,2,0))#修正箇所kA→kB
    plt.savefig(filename+"_{0:03d}.png".format(epoch))
    plt.show()

