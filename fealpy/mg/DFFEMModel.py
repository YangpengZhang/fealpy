import numpy as np
import csv
from scipy.sparse import coo_matrix, csr_matrix, eye, hstack, vstack, bmat, spdiags
import scipy.sparse
from fealpy.fem.integral_alg import IntegralAlg
from numpy.linalg import norm
from fealpy.fem import doperator
from fealpy.mg.DarcyFEMModel import DarcyP0P1
from scipy.sparse.linalg import cg, inv, dsolve,spsolve
from fealpy.functionspace.lagrange_fem_space import LagrangeFiniteElementSpace

class DarcyForchheimerP0P1():
    def __init__(self, pde, mesh, p, integrator):
        self.femspace = LagrangeFiniteElementSpace(mesh, p)
        self.pde = pde
        self.mesh = self.femspace.mesh

        self.uh = self.femspace.function()
        self.ph = self.femspace.function()
#        self.uI = self.femspace.function()
#        self.pI = self.femspace.interpolation(pde.pressure)

        self.cellmeasure = mesh.entity_measure('cell')
        self.integrator = integrator
        self.lfem = DarcyP0P1(self.pde, self.mesh, p, integrator)
        self.uh0,self.ph0 = self.lfem.solve()
        self.integralalg = IntegralAlg(self.integrator, self.mesh, self.cellmeasure)

    def gradbasis(self):
        mesh = self.mesh
        NC = mesh.number_of_cells()
        node = mesh.node
        cell = mesh.ds.cell

        ve1 = node[cell[:, 2],:] - node[cell[:, 1],:]
        ve2 = node[cell[:, 0],:] - node[cell[:, 2],:]
        ve3 = node[cell[:, 1],:] - node[cell[:, 0],:]
        area = 0.5*(-ve3[:, 0]*ve2[:, 1] + ve3[:, 1]*ve2[:, 0])

        Dlambda = np.zeros((NC,2,3))
        Dlambda[:,:,2] = np.c_[-ve3[:, 1]/(2*area), ve3[:, 0]/(2*area)]
        Dlambda[:,:,0] = np.c_[-ve1[:, 1]/(2*area), ve1[:, 0]/(2*area)]
        Dlambda[:,:,1] = np.c_[-ve2[:, 1]/(2*area), ve2[:, 0]/(2*area)]

        return Dlambda


    def get_left_matrix(self):
        femspace = self.femspace
        mesh = self.mesh
        cellmeasure = self.cellmeasure
        cell = mesh.ds.cell
        node = mesh.node

        NC = mesh.number_of_cells()
        NN = mesh.number_of_nodes()

        mu = self.pde.mu
        rho = self.pde.rho
        scaledArea = mu/rho*cellmeasure
        Dlambda = self.gradbasis()
        A11 = spdiags(np.r_[scaledArea,scaledArea], 0, 2*NC, 2*NC)

        ## Assemble gradient matrix for pressure
        I = np.arange(2*NC)
        data1 = Dlambda[:, 0, 0]*cellmeasure
        A12 = coo_matrix((data1, (I[:NC],cell[:, 0])), shape=(2*NC, NN))
        data2 = Dlambda[:, 1, 0]*cellmeasure
        A12 += coo_matrix((data2, (I[NC:],cell[:, 0])), shape=(2*NC, NN))
        
        data1 = Dlambda[:, 0, 1]*cellmeasure
        A12 += coo_matrix((data1, (I[:NC],cell[:, 1])), shape=(2*NC, NN))
        data2 = Dlambda[:, 1, 1]*cellmeasure
        A12 += coo_matrix((data2, (I[NC:],cell[:, 1])), shape=(2*NC, NN))

        data1 = Dlambda[:, 0, 2]*cellmeasure
        A12 += coo_matrix((data1, (I[:NC],cell[:, 2])), shape=(2*NC, NN))
        data2 = Dlambda[:, 1, 2]*cellmeasure
        A12 += coo_matrix((data2, (I[NC:],cell[:, 2])), shape=(2*NC, NN))
        A12 = A12.tocsr()
        A21 = A12.transpose()

        A = bmat([(A11, A12), (A21, None)], format='csr',dtype=np.float)

    
        return A

    def get_right_vector(self):
        mesh = self.mesh
        cellmeasure = self.cellmeasure
        node = mesh.node
        edge = mesh.ds.edge
        cell = mesh.ds.cell
        NN = mesh.number_of_nodes()

        bc = mesh.entity_barycenter('cell')
        ft = self.pde.f(bc)*np.c_[cellmeasure,cellmeasure]
        f = np.ravel(ft,'F')

        cell2edge = mesh.ds.cell_to_edge()
        ec = mesh.entity_barycenter('edge')
        mid1 = ec[cell2edge[:, 1],:]
        mid2 = ec[cell2edge[:, 2],:]
        mid3 = ec[cell2edge[:, 0],:]

        bt1 = cellmeasure*(self.pde.g(mid2) + self.pde.g(mid3))/6
        bt2 = cellmeasure*(self.pde.g(mid3) + self.pde.g(mid1))/6
        bt3 = cellmeasure*(self.pde.g(mid1) + self.pde.g(mid2))/6

        b = np.bincount(np.ravel(cell,'F'),weights=np.r_[bt1,bt2,bt3], minlength=NN)

        isBDEdge = mesh.ds.boundary_edge_flag()
        edge2node = mesh.ds.edge_to_node()
        bdEdge = edge[isBDEdge,:]
        ec = mesh.entity_barycenter('edge')
        d = np.sqrt(np.sum((node[edge2node[isBDEdge,0],:]\
                - node[edge2node[isBDEdge,1],:])**2,1))
        mid = ec[isBDEdge,:]
        ii = np.tile(d*self.pde.Neumann_boundary(mid)/2,(1,2))

        g = np.bincount(np.ravel(bdEdge,'F'),\
                weights=np.ravel(ii), minlength=NN)
        g = g - b

        
        return np.r_[f,g]

    def solve(self):
        mesh = self.mesh
        node = mesh.node
        edge = mesh.ds.edge
        cell = mesh.ds.cell
        cellmeasure = self.cellmeasure
        NN = mesh.number_of_nodes()
        NC = mesh.number_of_cells()
        A = self.get_left_matrix()
        A11 = A[:2*NC,:2*NC]
        A12 = A[:2*NC,2*NC:]
        A21 = A[2*NC:,:2*NC]
        b = self.get_right_vector()

        mu = self.pde.mu
        rho = self.pde.rho
        beta = self.pde.beta
        alpha = self.pde.alpha
        tol = self.pde.tol
        maxN = self.pde.maxN
        ru = 1
        rp = 1

        ## P-R iteration for D-F equation
        n = 0
        r = np.ones((2,maxN),dtype=np.float)
        area = np.r_[cellmeasure,cellmeasure]
        ##  Knowing (u,p), explicitly compute the intermediate velocity u(n+1/2)

        F = self.uh0/alpha - (mu/rho)*self.uh0 - (A12@self.ph0 - b[:2*NC])/area
        FL = np.sqrt(F[:NC]**2 + F[NC:]**2)
        gamma = 1.0/(2*alpha) + np.sqrt((1.0/alpha**2) + 4*(beta/rho)*FL)/2
        uhalf = F/np.r_[gamma,gamma]
        ## Direct Solver 

        Aalpha = A11 + spdiags(area/alpha, 0, 2*NC,2*NC)

        while ru+rp > tol and n < maxN:
            ## solve the linear Darcy equation
            uhalfL = np.sqrt(uhalf[:NC]**2 + uhalf[NC:]**2)
            fnew = b[:2*NC] + uhalf*area/alpha\
                    - beta/rho*uhalf*np.r_[uhalfL,uhalfL]*area

            ## Direct Solver
            Aalphainv = inv(Aalpha)
            Ap = A21@Aalphainv@A12
            bp = A21@(Aalphainv@fnew) - b[2*NC:]
            p = np.zeros(NN,dtype=np.float)
            p[1:] = spsolve(Ap[1:,1:],bp[1:])
            c = np.sum(np.mean(p[cell],1)*cellmeasure)/np.sum(cellmeasure)
            p = p - c
            u = Aalphainv@(fnew - A12@p)

            ## Step1:Solve the nonlinear Darcy equation

            F = u/alpha - (mu/rho)*u - (A12@p - b[:2*NC])/area
            FL = np.sqrt(F[:NC]**2 + F[NC:]**2)
            gamma = 1.0/(2*alpha) + np.sqrt((1.0/alpha**2) + 4*(beta/rho)*FL)/2
            uhalf = F/np.r_[gamma,gamma]

            ## Updated residual and error of consective iterations

            n = n + 1
            uLength = np.sqrt(u[:NC]**2 + u[NC:]**2)
            Lu = A11@u + (beta/rho)*np.tile(uLength*cellmeasure,(1,2))*u + A12@p
            ru = norm(b[:2*NC] - Lu)/norm(b[:2*NC])
            if norm(b[2*NC:]) == 0:
                rp = norm(b[2*NC:] - A21@u)
            else:
                rp = norm(b[2*NC:] - A21@u)/norm(b[2*NC:])

            self.uh0 = u
            self.ph0 = p
            r[0,n] = ru
            r[1,n] = rp

        self.u = u
        self.p = p
        return u,p

    def get_pL2_error(self):

        p = self.pde.pressure
        ph = self.ph.value

        pL2 = self.integralalg.L2_error(p,ph)
        return pL2

    def get_uL2_error(self):
        mesh = self.mesh
        bc = mesh.entity_barycenter('cell')
        uI = self.pde.velocity(bc)
        
        uh = self.uh.value
        u = self.pde.velocity



#        self.integralalg = IntegralAlg(self.integrator, self.mesh, self.cellmeasure)
        uL2 = self.integralalg.L2_error(u,uh)
        return uL2


    def get_H1_error(self):
        mesh = self.mesh
        gp = self.pde.grad_pressure
        u,p = self.solve()
        gph = p.grad_value
        H1 = self.integralalg.L2_error(gp, gph)
        return H1