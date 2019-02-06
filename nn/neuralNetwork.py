import torch
import torch.nn as nn
import numpy as np
from data_featured.dataset_featured import DatasetFeatures
import matplotlib.pyplot as plt

class NN(object):
    def __init__(self, data:DatasetFeatures, utils, FPrate, discount, att_type):
        self.data = data
        self.utils = utils # function
        self.FPrate = FPrate
        self.discount = discount
        self.att_type = att_type

        self.BATCH_SIZE =  64
        self.LR_G = 0.0001  # learning rate for generator
        self.LR_D = 0.0001  # learning rate for discriminator
        self.latent = 10  # think of this as number of ideas for generating an art work (Generator)
        self.dim = len(self.data.features)  # it could be total point G can draw in the canvas
        self.num_of_gens = 8
        self.seed = 42


    def sample_data(self):     # painting from the famous artist (real target)
        # samples = self.data.data.sample(self.BATCH_SIZE, random_state=np.random.RandomState)
        samples = self.data.data.sample(self.BATCH_SIZE) #, random_state=self.seed)
        samples = samples.as_matrix()
        # samples = samples[:, np.newaxis]
        return torch.from_numpy(samples).float()

    def solve(self):
        torch.manual_seed(self.seed)
        plt.ion() # something with continuous presentation of the plots

        # G = nn.Sequential(                      # Generator
        #     nn.Linear(self.latent, 16),            # random ideas (could from normal distribution)
        #     nn.ReLU(),
        #     nn.Linear(16, self.dim),
        #     nn.ReLU()
        #     # nn.Sigmoid(),     # making a painting from these random ideas
        # )


        Gs = [nn.Sequential(                      # Generator
            nn.Linear(self.latent, 16),            # random ideas (could from normal distribution)
            nn.ReLU(),
            nn.Linear(16, self.dim),
            nn.ReLU()
        ) for _ in range(self.num_of_gens)]

        D = nn.Sequential(                      # Discriminator
            nn.Linear(self.dim, 256),     # receive art work either from the famous artist or a newbie like G
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Sigmoid(),                       # tell the probability that the art work is made by artist
        )

        self.reset_model(D,0.01)
        for G in Gs:
            self.reset_model(G,1)

        opt_D = torch.optim.Adam(D.parameters(), lr=self.LR_D)
        # opt_G = torch.optim.Adam(G.parameters(), lr=self.LR_G)
        opt_Gs =  [torch.optim.Adam(x.parameters(), lr=self.LR_G) for x in Gs]

        fig, ax = plt.subplots(2, 3)
        for step in range(30000):
            real_samples = self.sample_data()           # real painting from artist
            latent_samples = torch.rand(self.BATCH_SIZE, self.latent)  # random ideas
            gen_samples = [G(latent_samples) for G in Gs]

            prob_of_insp_real = D(real_samples)  # D try to reduce this prob
            prob_of_insp_fake = [D(gen_sample) for gen_sample in gen_samples]

            utils = [gen_sample[:,0] for gen_sample in gen_samples]

            # D_loss = - (-torch.mul(torch.clamp(torch.mean(prob_of_insp_real) - 0.1, min=0), 100) - torch.mean( torch.mul(1 - prob_of_insp_fake, utils)))
            # D_loss = - (-torch.mul(torch.clamp(torch.mean(prob_of_insp_real) - 0.1, min=0), 100) - torch.mean( torch.mul(1 - prob_of_insp_fake, utils))-torch.mean( torch.mul(1 - prob_of_insp_fake2, utils2)))
            # D_loss = - (-torch.mul(torch.clamp(torch.mean(prob_of_insp_real) - 0.1, min=0), 100)
            #             - [torch.mean(torch.mul(1-prob_of_insp_fake_single, util)) for prob_of_insp_fake_single, util in zip(prob_of_insp_fake, utils)].sum())

            D_loss = - (-torch.mul(torch.clamp(torch.mean(prob_of_insp_real) - 0.1, min=0), 100)
                        - torch.mean(torch.mul(1-torch.cat(prob_of_insp_fake,0), torch.cat(utils, 0))))

            G_loss = [-torch.mean(torch.mul(1-prob_of_insp_fake_single, util_single)) for prob_of_insp_fake_single, util_single in zip(prob_of_insp_fake, utils)]

            opt_D.zero_grad()
            D_loss.backward(retain_graph=True)  # reusing computational graph
            opt_D.step()

            for opt_G in opt_Gs:
                opt_G.zero_grad()
            for G in G_loss:
                G.backward()
            for opt_G in opt_Gs:
                opt_G.step()


            if step % 400 == 0:  # plotting
                print("D_loss {}, FP {}, G_loss {}".format(D_loss, torch.mean(prob_of_insp_real), G_loss))
                print("FP {}, loss {}".format(torch.mean(prob_of_insp_real),
                    torch.mean(torch.mul(1 - torch.cat(prob_of_insp_fake,0), torch.cat(utils,0)))
                ))

                self.plot(D, ax, gen_samples, real_samples)

                plt.tight_layout()
                plt.show()
                plt.pause(0.0001)
                D.train()

        # plt.ioff()

    def plot(self, D, ax, gen_samples, real_samples):
        if len(self.data.feature_size) == 1:

            ax[0, 0].cla()
            ax[0, 0].hist(real_samples.data.numpy(), density=True)
            ax[0, 0].set_xlim(self.data.limits[0])
            ax[0, 0].set_ylim([0, 1])

            ax[1, 2].cla()
            ax[1, 2].hist(gen_samples.data.numpy(), density=True)
            ax[1, 2].set_xlim(self.data.limits[0])
            ax[1, 2].set_ylim([0, 1])

            D.eval()
            t = torch.from_numpy(np.linspace(self.data.mins[0], self.data.maxs[0], 101)[:, np.newaxis]).float()
            ax[0, 1].cla()
            ax[0, 1].plot(t.numpy().T[0], D(t).data.numpy().T[0], 'g-')
            ax[0, 1].set_xlim(self.data.limits[0])
            ax[0, 1].set_ylim([0, 1])

            ax[1, 0].cla()
            ax[1, 0].plot(t.numpy().T[0], (1 - D(t).data.numpy().T[0]) * t.numpy().T[0], 'r-')
            ax[1, 0].set_xlim(self.data.limits[0])
            ax[1, 0].set_ylim([0, 1])

        elif len(self.data.feature_size) == 2:
            ax[0, 0].cla()
            real_samples_np = real_samples.data.numpy().T
            # ax[0,0].hist2d(real_samples_np[0], real_samples_np[1])
            ax[0, 0].plot(real_samples_np[0], real_samples_np[1], 'b.')
            ax[0, 0].set_xlim(self.data.limits[0])
            ax[0, 0].set_ylim(self.data.limits[1])

            gen_samples_np = [sam.data.numpy().T for sam in gen_samples]
            ax[1, 2].cla()
            for gen in gen_samples_np:
                ax[1, 2].plot(gen[0], gen[1], 'r.')
            # ax[1, 2].plot(gen_samples_np[0], gen_samples_np[1], 'b.')
            # ax[1,2].hist2d(gen_samples_np[0], gen_samples_np[1])
            # ax[1, 2].set_xlim(left=0)
            # ax[1, 2].set_ylim(bottom=0)
            # ax[1, 2].set_xlim(self.data.limits[0])
            # ax[1, 2].set_ylim(self.data.limits[1])

            D.eval()
            # t = torch.from_numpy(np.linspace(self.data.mins[0], self.data.maxs[0], 101)[:, np.newaxis]).float()

            spaces = [np.linspace(
                min(self.data.mins[d], min(list(map(lambda x: x[d].min(), gen_samples_np)))),
                max(self.data.maxs[d], max(list(map(lambda x: x[d].max(), gen_samples_np)))), 101) for d in
                      range(len(self.data.feature_size))]
            x = np.meshgrid(*spaces)
            mesh = np.stack([xsub.ravel() for xsub in x], axis=-1)
            mesh_ts = torch.from_numpy(mesh).float()
            def_mesh_ts = D(mesh_ts).data.numpy().reshape(x[0].shape)
            limits1 = [mesh.T[0].min(), mesh.T[0].max()]
            limits2 = [mesh.T[1].min(), mesh.T[1].max()]
            ex = limits1 + limits2

            ax[0, 1].cla()
            ax[0, 1].imshow(def_mesh_ts, cmap=plt.cm.gist_earth_r, extent=ex, interpolation='nearest', origin='lower', aspect='auto')
            for gen in gen_samples_np:
                ax[0, 1].plot(gen[0], gen[1], 'r.')
            ax[0, 1].plot(real_samples_np[0], real_samples_np[1], 'b.')
            ax[0, 1].set_xlim(left=0)
            ax[0, 1].set_ylim(bottom=0)

            ax[1, 0].cla()
            ax[1, 0].imshow(((1 - def_mesh_ts) * mesh[:, 0].reshape(x[0].shape)), cmap=plt.cm.gist_earth_r, extent=ex,
                interpolation='nearest', origin='lower', aspect='auto')
            ax[0, 1].set_xlim(left=0)
            ax[0, 1].set_ylim(bottom=0)

    def reset_model(self, M, c):
        def init_weights(m):
            if type(m) == nn.Linear:
                torch.nn.init.xavier_uniform_(m.weight)
                m.bias.data.fill_(c)

        M.apply(init_weights)
