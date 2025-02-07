# -*- coding: utf-8 -*-
"""
Created on Wed Jul 12 16:11:15 2023

@author: Md Tauhidul Islam, Ph.D., Dept. of Radiation Oncology, Stanford University
"""

from tensorflow.keras.optimizers import Adam
from genomap.utils.ConvIDEC import ConvIDEC
from sklearn.feature_selection import VarianceThreshold
from genomap.genomap import construct_genomap
import umap
from genomap.utils.gTraj_utils import nearest_divisible_by_four
import scanpy as sc
import numpy as np
import pandas as pd
from genomap.utils.util_Sig import select_n_features

def genoVis(data,n_clusters=None, colNum=32,rowNum=32,batch_size=64,verbose=1,
                    pretrain_epochs=100,maxiter=300):
# rowNum and colNum are the row and column numbers of constructed genomaps
# n_clusters: number of data classes in the data
# batch_size: number of samples in each mini batch while training the deep neural network
# verbose: whether training progress will be shown or not
# pretrain_epochs: number of epoch for pre-training the CNN
# maxiter: number of epoch of fine-tuning training
# Construction of genomap    
    colNum=nearest_divisible_by_four(colNum)
    rowNum=nearest_divisible_by_four(rowNum)
    nump=rowNum*colNum 
    if nump<data.shape[1]:
        data,index=select_n_features(data,nump)
    genoMaps=construct_genomap(data,rowNum,colNum,epsilon=0.0,num_iter=200)
    
    if n_clusters==None:
        
        adata = convertToAnnData(data)
        # Perform Louvain clustering
        sc.pp.neighbors(adata)
        sc.tl.louvain(adata, resolution=1.0)
        # Access the cluster assignments
        cluster_labels = adata.obs['louvain']
        n_clusters = len(np.unique(cluster_labels)) 

    # Deep learning-based dimensionality reduction and clustering
    optimizer = Adam()    
    model = ConvIDEC(input_shape=genoMaps.shape[1:], filters=[32, 64, 128, 32], n_clusters=n_clusters)
    model.compile(optimizer=optimizer, loss=['kld', 'mse'], loss_weights=[0.1, 1.0])
    pretrain_optimizer ='adam'
    update_interval=50
    model.pretrain(genoMaps, y=None, optimizer=pretrain_optimizer, epochs=pretrain_epochs, batch_size=batch_size,
                        verbose=verbose)

    y_pred = model.fit(genoMaps, y=None, maxiter=maxiter, batch_size=batch_size, update_interval=update_interval,
                       )
    # Perform clustering using genomap
    y_pred = model.predict_labels(genoMaps)
    # Extract the autoencoder features
    feat_DNN=model.extract_features(genoMaps)
    # Create embeddings from the extracted features
    embedding2D = umap.UMAP(n_neighbors=30,min_dist=0.3,n_epochs=200).fit_transform(feat_DNN)
    return embedding2D, y_pred


def convertToAnnData(data):
    # Convert numpy array to annData
    # Create pseudo cell names
    cell_names = ['Cell_' + str(i) for i in range(1, data.shape[0]+1)]
    # Create pseudo gene names
    gene_names = ['Gene_' + str(i) for i in range(1, data.shape[1]+1)]
    # Create a pandas DataFrame
    df = pd.DataFrame(data, index=cell_names, columns=gene_names)
    adataMy=sc.AnnData(df)
    return adataMy

