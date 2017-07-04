import numpy as np

class BihamonicData2:
    def __init__(self,a,b):
        self.a = a
        self.b = b

    def solution(self,p):
        """ The exact solution 
        """
        a = self.a
        b = self.b
        x = p[:, 0]
        y = p[:, 1]
        r = 2350*(x**4)*(x-a)*(x-a)*(y**4)*(y-b)*(y-b)
        return r

    def gradient(self,p):
        x = p[:, 0]
        y = p[:, 1]
        a = self.a
        b = self.b
        val = np.zeros((len(x), 2), dtype=p.dtype)
        val[:,0] = 2350*2*(x**3)*(x-a)*(3*x-2*a)*(y**4)*(y-b)*(y-b)
        val[:,1] = 2350*(x**4)*(x-a)*(x-a)*2*(y**3)*(y-b)*(3*y-2*b)
        return val

    def laplace(self,p):
        x = p[:, 0]
        y = p[:, 1]
        a = self.a
        b = self.b
        r = 2350*(y**6-2*b*y**5+b**2*y**4)*(30*x**4-40*a*x**3+12*a**2*x**2)
        r += 2350*(x**6-2*a*x**5+a**2*x**4)*(30*y**4-40*b*y**3+12*b**2*y**2)
        return r


    def dirichlet(self, p):
        """ Dilichlet boundary condition
        """
        return np.zeros((p.shape[0],), dtype=np.float)

    def neuman(self, p, n):
        """ Neuman boundary condition
        """
        return np.zeros((p.shape[0],), dtype=np.float)

    def source(self,p):
        x = p[:, 0]
        y = p[:, 1]
        a = self.a
        b = self.b
        r1 = 56400*(a**2-10*a*x+15*x**2)*(b-y)*(b-y)*y**4
        r2 = 18800*x**2*(6*a**2-20*a*x+15*x**2)*y**2*(6*b**2-20*b*y+15*y**2)
        r3 = 56400*(a-x)*(a-x)*x**4*(b**2-10*b*y+15*y**2)
        r = r1 + r2 + r3
        return r

    def is_boundary_dof(self, p):
        eps = 1e-14 
        return (p[:,0] < eps) | (p[:,1] < eps) | (p[:, 0] > 1.0 - eps) | (p[:, 1] > 1.0 - eps)

class BihamonicData3:
    def __init__(self,C):
        self.C = C

    def solution(self, p):
        pass

    def gradient(self, p):
        pass

    def laplace(self, p):
        pass

    def dirichlet(self, p):
        """ Dilichlet boundary condition
        """
        return np.zeros((p.shape[0],), dtype=np.float)

    def source(self,p):
        r = C
        return r

class BihamonicData4:
    def __init__(self):
        pass
    
    def solution(self, p):
        """ The exact solution 
        """
        x = p[:, 0]
        y = p[:, 1]
        pi = np.pi
        r = np.sin(2*pi*x)*np.sin(2*pi*y)
        return r

    def gradient(self,p):
        x = p[:, 0]
        y = p[:, 1]
        pi = np.pi
        val = np.zeros((len(x), 2), dtype=p.dtype)
        val[:,0] = 2*pi*np.cos(2*pi*x)*np.sin(2*pi*y) 
        val[:,1] = 2*pi*np.cos(2*pi*y)*np.sin(2*pi*x)
        return val


    def laplace(self,p):
        x = p[:, 0]
        y = p[:, 1]
        pi = np.pi
        r = -8*pi**2*self.solution(p)
        return r


    def dirichlet(self, p):
        """ Dilichlet boundary condition
        """
        return np.zeros((p.shape[0],), dtype=np.float)

    def neuman(self, p, n):
        """ Neuman boundary condition
        """
        val = self.gradient(p)
        return np.sum(val*n, axis=1)

    def source(self,p):
        x = p[:, 0]
        y = p[:, 1]
        pi = np.pi
        r = 64*pi**4*np.sin(2*pi*x)*np.sin(2*pi*y)
        return r

    def is_boundary_dof(self, p):
        eps = 1e-14 
        return (p[:,0] < eps) | (p[:,1] < eps) | (p[:, 0] > 1.0 - eps) | (p[:, 1] > 1.0 - eps)


