'''
DCGAN on FACES using Keras
keras 2.0.6
'''

import numpy as np
import time

from keras import backend as K
from keras.models import Sequential
from keras.layers import Dense, Activation, Flatten, Reshape
from keras.layers import Conv2D, Conv2DTranspose, UpSampling2D
from keras.layers import LeakyReLU, Dropout
from keras.layers import BatchNormalization
from keras.optimizers import Adam, RMSprop
from keras.preprocessing.image import img_to_array, array_to_img, load_img, list_pictures
from keras.preprocessing.image import ImageDataGenerator

import matplotlib.pyplot as plt

from PIL import Image

# enable multi-CPU
#import theano
#theano.config.openmp = True

random_size = 100

class ElapsedTimer(object):
    def __init__(self):
        self.start_time = time.time()
    def elapsed(self,sec):
        if sec < 60:
            return str(sec) + " sec"
        elif sec < (60 * 60):
            return str(sec / 60) + " min"
        else:
            return str(sec / (60 * 60)) + " hr"
    def elapsed_time(self):
        print("Elapsed: %s " % self.elapsed(time.time() - self.start_time) )

class DCGAN(object):
    def __init__(self, img_rows=48, img_cols=48, channel=1):

        self.img_rows = img_rows
        self.img_cols = img_cols
        self.channel = channel
        self.D = None   # discriminator
        self.G = None   # generator
        self.AM = None  # adversarial model
        self.DM = None  # discriminator model

    # (W-F+2P)/S+1
    def discriminator(self):
        if self.D:
            return self.D
        self.D = Sequential()
        depth = 64#128
        dropout = 0.4
        # In: 48 x 48 x 1, depth = 1
        # Out: 24 x 24 x 1, depth=64
        input_shape = (self.img_rows, self.img_cols, self.channel)
        self.D.add(Conv2D(depth*1, 5, strides=2, input_shape=input_shape,\
            padding='same'))
        self.D.add(LeakyReLU(alpha=0.2))
        self.D.add(Dropout(dropout))

        self.D.add(Conv2D(depth*2, 5, strides=2, padding='same'))
        self.D.add(LeakyReLU(alpha=0.2))
        self.D.add(Dropout(dropout))

        self.D.add(Conv2D(depth*4, 5, strides=2, padding='same'))
        self.D.add(LeakyReLU(alpha=0.2))
        self.D.add(Dropout(dropout))

        self.D.add(Conv2D(depth*8, 5, strides=1, padding='same'))
        self.D.add(LeakyReLU(alpha=0.2))
        self.D.add(Dropout(dropout))

        # Out: 1-dim probability
        self.D.add(Flatten())
        self.D.add(Dense(1))
        self.D.add(Activation('sigmoid'))
        self.D.summary()
        return self.D

    def generator(self):
        if self.G:
            return self.G
        self.G = Sequential()
        dropout = 0.4
        depth = 64+64+64+64#+64
        dim = 12
        # In: random_size
        # Out: dim x dim x depth
        self.G.add(Dense(dim*dim*depth, input_dim=random_size))
        self.G.add(BatchNormalization(momentum=0.9))
        self.G.add(Activation('relu'))
        self.G.add(Reshape((dim, dim, depth)))
        self.G.add(Dropout(dropout))

        # In: dim x dim x depth
        # Out: 2*dim x 2*dim x depth/2
        self.G.add(UpSampling2D())
        self.G.add(Conv2DTranspose(int(depth/2), 5, padding='same'))
        self.G.add(BatchNormalization(momentum=0.9))
        self.G.add(Activation('relu'))

        self.G.add(UpSampling2D())
        self.G.add(Conv2DTranspose(int(depth/4), 5, padding='same'))
        self.G.add(BatchNormalization(momentum=0.9))
        self.G.add(Activation('relu'))

        self.G.add(Conv2DTranspose(int(depth/8), 5, padding='same'))
        self.G.add(BatchNormalization(momentum=0.9))
        self.G.add(Activation('relu'))

        # Out: 50 x 50 x 1 grayscale image [0.0,1.0] per pix
        self.G.add(Conv2DTranspose(1, 5, padding='same'))
        self.G.add(Activation('sigmoid'))
        self.G.summary()
        return self.G

    def discriminator_model(self):
        if self.DM:
            return self.DM
        optimizer = RMSprop(lr=0.0002, decay=6e-8)
        self.DM = Sequential()
        self.DM.add(self.discriminator())
        self.DM.compile(loss='binary_crossentropy', optimizer=optimizer,\
            metrics=['accuracy'])
        return self.DM

    def adversarial_model(self):
        if self.AM:
            return self.AM
        optimizer = RMSprop(lr=0.0001, decay=3e-8)
        self.AM = Sequential()
        self.AM.add(self.generator())
        self.AM.add(self.discriminator())
        self.AM.compile(loss='binary_crossentropy', optimizer=optimizer,\
            metrics=['accuracy'])
        return self.AM

class FACE_DCGAN(object):
    def __init__(self):
        self.img_rows = 48
        self.img_cols = 48
        self.channel = 1
        self.datagen = ImageDataGenerator(
			rotation_range=10,
			width_shift_range=0.1,
			height_shift_range=0.1,
			zoom_range=0.1,
			rescale=1./255.,
			horizontal_flip=True)

        X = []
        for picture in list_pictures('A', ext='png'):
            img = img_to_array(load_img(picture, grayscale=True).resize((self.img_rows,self.img_cols)))
            X.append(img)
        self.x_train = np.asarray(X)

        print(self.x_train.shape)

        # Check Keras backend
        if(K.image_dim_ordering()=="th"):
            # Reshape the data to be used by a Theano CNN. Shape is
            # (nb_of_samples, nb_of_color_channels, img_width, img_heigh)
            self.x_train = self.x_train.reshape(-1, 1, self.img_rows, self.img_cols).astype(np.float32)
        else:
            # Reshape the data to be used by a Tensorflow CNN. Shape is
            # (nb_of_samples, img_width, img_heigh, nb_of_color_channels)
            self.x_train = self.x_train.reshape(-1, self.img_rows, self.img_cols, 1).astype(np.float32)

        self.DCGAN = DCGAN()
        self.discriminator =  self.DCGAN.discriminator_model()
        self.adversarial = self.DCGAN.adversarial_model()
        self.generator = self.DCGAN.generator()

    def train(self, train_steps, batch_size=256, save_interval=0):

        N = 50
        X_batch = []
        for i in range(N):
            X_batch.append( self.datagen.flow(self.x_train, batch_size=1000).next() ) # TODO : size hardcoded
        X_batch = np.array(X_batch).reshape(N*1000,self.img_rows,self.img_cols,1)
        print(X_batch.shape)

        #plt.imshow(X_batch[25000,:,:,0], cmap='gray')
        #plt.show()
        #im = Image.fromarray(X_batch[25000,:,:,0])
        #im.save("test_input.tiff")

        for i in range(train_steps):

            images_train = X_batch[np.random.randint(0,
                X_batch.shape[0], size=batch_size), :, :, :]
            noise = np.random.uniform(-1.0, 1.0, size=[batch_size, random_size])
            images_fake = self.generator.predict(noise)
            x = np.concatenate((images_train, images_fake))
            y = np.ones([2*batch_size, 1])
            y[batch_size:, :] = 0
            d_loss = self.discriminator.train_on_batch(x, y)

            y = np.ones([batch_size, 1])
            noise = np.random.uniform(-1.0, 1.0, size=[batch_size, random_size])

            # launch training on given batch
            a_loss = self.adversarial.train_on_batch(noise, y)

            log_mesg = "%d: [D loss: %f, acc: %f]" % (i, d_loss[0], d_loss[1])
            log_mesg = "%s  [A loss: %f, acc: %f]" % (log_mesg, a_loss[0], a_loss[1])
            print(log_mesg)

            if save_interval>0:
                if (i+1)%save_interval==0:
                    noise_input = np.random.uniform(-1.0, 1.0, size=[16, random_size])
                    self.plot_images(save2file=True, step=(i+1))

    def save_gen_image(self):
        noise = np.random.uniform(-1.0, 1.0, size=[1, random_size])
        img = Image.fromarray(self.generator.predict(noise).reshape(self.img_rows,self.img_cols))
        img.save("test_gen.tiff")

    def plot_images(self, save2file=False, fake=True, step=0):
        mosaic_filename = 'undefined.png'
        if fake:
            noise = np.random.uniform(-1.0, 1.0, size=[16, random_size])
            images = self.generator.predict(noise)
            if step == 0:
                mosaic_filename = "face_noise_final.png"
            else:
                mosaic_filename = "face_noise_step%d.png" % step
        else:
            i = np.random.randint(0, self.x_train.shape[0], 16)
            images = self.x_train[i, :, :, :]
            mosaic_filename = "face_true.png"

        plt.figure(figsize=(10,10))
        for i in range(images.shape[0]):
            plt.subplot(4, 4, i+1)
            image = images[i, :, :, :]
            image = np.reshape(image, [self.img_rows, self.img_cols])
            plt.imshow(image, cmap='gray')
            plt.axis('off')
        plt.tight_layout()

        if save2file:
			# save single file
            if step != 0:
                img = Image.fromarray(images[0].reshape(self.img_rows,self.img_cols))
                img.save("test_step%d.tiff" % step)
			# save mosaic
            plt.savefig(mosaic_filename)
            plt.close('all')

        plt.show()

if __name__ == '__main__':
    face_dcgan = FACE_DCGAN()
    timer = ElapsedTimer()
    #face_dcgan.train(train_steps=10000, batch_size=256, save_interval=500)
    face_dcgan.train(train_steps=30, batch_size=256, save_interval=5)
    timer.elapsed_time()
    face_dcgan.save_gen_image() # save single generated image
    face_dcgan.plot_images(fake=True, save2file=True) # save gallery of generated images
    face_dcgan.plot_images(fake=False, save2file=True) # save gallery of real training images
