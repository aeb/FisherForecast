import numpy as np
import matplotlib.pyplot as plt
import scipy.special as ss
import scipy.interpolate as si
import ehtim as eh
import copy
import hashlib
import themispy as ty

class FisherForecast :
    """
    Class that collects and contains information for making Fisher-matrix type
    forecasts for observations of various types.  Forms a base class for fully
    analytical versions that may be application specific.
    """

    def __init__(self) :
        self.size = 0
        self.argument_hash = None
        
        
    def visibilities(self,u,v,p,verbosity=0) :
        """
        Generates visibilities associated with a given model image object.  Note 
        that this uses FFTs to create the visibilities and then interpolates.

        Args:
          u (np.array): list of u positions in units of :math:`\\lambda`.
          v (np.array): list of v positions in units of :math:`\\lambda`.
          p (np.array): list of parameters for the model image used to create object.
          verbosity (int): Verbosity level. 0 prints nothing. 1 prints various elements of the plotting process. Passed to :func:`model_image.generate_intensity_map`. Default: 0.

        Returns:
          V (np.array): list of complex visibilities computed at u,v.
        """

        raise(RuntimeError("visbilities function not implemented in base class!"))
        
        # Return something
        return 0*u

            
    def visibility_gradients(self,u,v,p,verbosity=0) :
        """
        Generates visibilities associated with a given model image object.  Note 
        that this uses FFTs to create the visibilities and then interpolates.

        Args:
          u (np.array): list of u positions in units of :math:`\\lambda`.
          v (np.array): list of v positions in units of :math:`\\lambda`.
          p (np.array): list of parameters for the model image used to create object.
          verbosity (int): Verbosity level. 0 prints nothing. 1 prints various elements of the plotting process. Passed to :func:`model_image.generate_intensity_map`. Default: 0.

        Returns:
          gradV (np.ndarray): list of complex visibilities gradients computed at u,v.
        """

        raise(RuntimeError("visbility_gradients function not implemented in base class!"))

        # Return something    
        return 0*u


    def parameter_labels(self) :

        raise(RuntimeError("parameter_labels function not implemented in base class!"))

        return []


    def fisher_covar(self,u,v,sig,p,**kwargs) :
        # Get the fisher covariance 
        gradV = self.visibility_gradients(u,v,p,**kwargs)
        covar = np.zeros((self.size,self.size))
        for i in range(self.size) :
            for j in range(self.size) :
                covar[i][j] = np.sum( np.conj(gradV[:,i])*gradV[:,j]/sig**2 )
            
        return covar

    def fisher_covar_from_obs(self,obs,p,**kwargs) :
        new_argument_hash = hashlib.md5(bytes(str(obs)+str(p),'utf-8')).hexdigest()
        if ( new_argument_hash == self.argument_hash ) :
            return self.covar
        else :
            self.argument_hash = new_argument_hash
            u = obs.data['u']
            v = obs.data['v']
            sig = obs.data['sigma']
            self.covar = self.fisher_covar(u,v,sig,p,**kwargs)
        return self.covar

    def uniparameter_uncertainties_from_obs(self,obs,p,**kwargs) :
        C = 2.0*self.fisher_covar_from_obs(obs,p,**kwargs)
        Sig_uni = np.zeros(self.size)
        ilist = np.arange(self.size)
        for i in ilist :
            N = C[i][i]
            Sig_uni[i] = np.sqrt(2.0/N)
        return Sig_uni

    def marginalized_uncertainties_from_obs(self,obs,p,**kwargs) :
        C = 2.0*self.fisher_covar_from_obs(obs,p,**kwargs)
        Sig_marg = np.zeros(self.size)
        M = np.zeros((self.size-1,self.size-1))
        v = np.zeros(self.size-1)
        ilist = np.arange(self.size)
        for i in ilist :
            ini = ilist[ilist!=i]
            for j2,j in enumerate(ini) :
                for k2,k in enumerate(ini) :
                    M[j2,k2] = C[j][k]
                v[j2] = C[i][j]
            N = C[i][i]
            Minv = np.linalg.inv(M)
            mN = N - np.matmul(v,np.matmul(Minv,v))
            Sig_marg[i] = np.sqrt(2.0/mN)
        return Sig_marg

    def uncertainties_from_obs(self,obs,p,**kwargs) :
        C = 2.0*self.fisher_covar_from_obs(obs,p,**kwargs)

        # print("FOO:",C)
        
        Sig_uni = np.zeros(self.size)
        Sig_marg = np.zeros(self.size)
        M = np.zeros((self.size-1,self.size-1))
        v = np.zeros(self.size-1)
        ilist = np.arange(self.size)
        for i in ilist :
            ini = ilist[ilist!=i]
            for j2,j in enumerate(ini) :
                for k2,k in enumerate(ini) :
                    M[j2,k2] = C[j][k]
                v[j2] = C[i][j]
            N = C[i][i]
            Minv = np.linalg.inv(M)
            mN = N - np.matmul(v,np.matmul(Minv,v))

            # print("BAR: %5g %15.8g %15.8g"%(i,N,mN))


            # mN = np.maximum(1e-6*N,mN)
            
            Sig_uni[i] = np.sqrt(2.0/N)
            Sig_marg[i] = np.sqrt(2.0/mN)

        return Sig_uni,Sig_marg


    def joint_biparameter_chisq(self,obs,p,i1,i2,**kwargs) :
        C = 2.0*self.fisher_covar_from_obs(obs,p,**kwargs)
        M = np.zeros((self.size-2,self.size-2))
        v1 = np.zeros(self.size-2)
        v2 = np.zeros(self.size-2)
        ilist = np.arange(self.size)
        
        ini12 = ilist[(ilist!=i1)*(ilist!=i2)]
        for j2,j in enumerate(ini12) :
            for k2,k in enumerate(ini12) :
                M[j2,k2] = C[j][k]
            v1[j2] = C[i1][j]
            v2[j2] = C[i2][j]
        N1 = C[i1][i1]
        N2 = C[i2][i2]
        C12 = C[i1][i2]

        Minv = np.linalg.inv(M)
        mN1 = N1 - np.matmul(v1,np.matmul(Minv,v1))
        mN2 = N2 - np.matmul(v2,np.matmul(Minv,v2))
        mC12 = C12 - 0.5*(np.matmul(v1,np.matmul(Minv,v2)) + np.matmul(v2,np.matmul(Minv,v1)))

        # Find range with eigenvectors/values
        l1 = 0.5*( (mN1+mN2) + np.sqrt( (mN1-mN2)**2 + 4.0*mC12**2 ) )
        l2 = 0.5*( (mN1+mN2) - np.sqrt( (mN1-mN2)**2 + 4.0*mC12**2 ) )

        e1 = np.array( [ mC12, l1-mN1 ] )
        e2 = np.array( [ e1[1], -e1[0] ] )
        # e2 = np.array( [ l2-mN2, mC12 ] )
        e1 = e1/ np.sqrt( e1[0]**2+e1[1]**2 )
        e2 = e2/ np.sqrt( e2[0]**2+e2[1]**2 )


        # l1 = max(1e-6*N1,l1)
        # l2 = max(1e-6*N2,l2)

        # print("BAZ:",i1,i2,l1,l2)
        
        if (l1<=0 or l2<=0) :
            print("Something's wrong! Variances are nonpositive!")
            print(i1,i2)
            print(l1,l2)
            print(N1,N2,C12)
            print(mN1,mN2,mC12)
            print(C)

        if (l1>l2 ):
            Sig_maj = np.sqrt(1.0/l2)
            Sig_min = np.sqrt(1.0/l1)
            e_maj = np.copy(e2)
            e_min = np.copy(e1)
        else :
            Sig_maj = np.sqrt(1.0/l1)
            Sig_min = np.sqrt(1.0/l2)
            e_maj = np.copy(e1)
            e_min = np.copy(e2)

        # dp1 = max( 4.5*Sig_maj*np.abs(e_maj[0]), 4.5*Sig_min*np.abs(e_min[0]) )
        # dp2 = max( 4.5*Sig_maj*np.abs(e_maj[1]), 4.5*Sig_min*np.abs(e_min[1]) )
        dp1 = 4.5*( Sig_maj*np.abs(e_maj[0]) + Sig_min*np.abs(e_min[0]) )
        dp2 = 4.5*( Sig_maj*np.abs(e_maj[1]) + Sig_min*np.abs(e_min[1]) )

        # if (i2==28) :
        #     print("FOO:",i1,i2,dp1,dp2,Sig_maj,Sig_min,abs(e_maj[0]),abs(e_min[0]),e_maj[0]*e_min[0]+e_maj[1]*e_min[1])
        #     print("    ",l1,l2,e1,e2)
        #     print("    ",mN1,mN2,mC12)

            
        Npx = int(max(128,min(16*Sig_maj/Sig_min,1024)))
        p1,p2 = np.meshgrid(np.linspace(-dp1,dp1,Npx),np.linspace(-dp2,dp2,Npx))
        csq = N1*p1**2 + 2*C12*p1*p2 + N2*p2**2
        mcsq = mN1*p1**2 + 2*mC12*p1*p2 + mN2*p2**2

        return p1,p2,csq,mcsq



class FF_model_image(FisherForecast) :
    """
    
    FisherForecast from ThemisyPy model_image objects.  Uses FFTs and centered 
    finite-difference to compute the visibilities and gradients.  May not always
    produce sensible behaviors.

    Args:
      img (model_image): A ThemisPy model_image object.

    Attributes:
      img (model_image): The ThemisPy model_image object for which to make forecasts.
    """

    def __init__(self,img) :
        super().__init__()
        self.img = img
        self.size = self.img.size

    def visibilities(self,u,v,p,limits=None,shape=None,padding=4,verbosity=0) :
        """
        Generates visibilities associated with a given model image object.  Note 
        that this uses FFTs to create the visibilities and then interpolates.

        Args:
          u (np.array): list of u positions in units of :math:`\\lambda`.
          v (np.array): list of v positions in units of :math:`\\lambda`.
          p (np.array): list of parameters for the model image used to create object.
          limits (list): May be single number, list with four elements specifying in :math:`\\mu as` the symmetric limits or explicit limits in [xmin,xmax,ymin,ymax] order.  Default: 100.
          shape (list): May be single number or list with two elements indicating the number of pixels in the two directions.  Default: 256.
          padding (int): Factor by which to pad image with zeros prior to FFT.  Default: 4.
          verbosity (int): Verbosity level. 0 prints nothing. 1 prints various elements of the plotting process. Passed to :func:`model_image.generate_intensity_map`. Default: 0.

        Returns:
          V (np.array): list of complex visibilities computed at u,v.
        """

        # Generate the image at current location
        self.img.generate(p)

        # Fix image limits
        if (limits is None) :
            limits = [-100,100,-100,100]
        elif (isinstance(limits,list)) :
            limits = limits
        else :
            limits = [-limits, limits, -limits, limits]

        # Set shape
        if (shape is None) :
            shape = [256, 256]
        elif (isinstance(shape,list)) :
            shape = shape
        else :
            shape = [shape, shape]
            
        if (verbosity>0) :
            print("limits:",limits)
            print("shape:",shape)

        if (len(u) != len(v)) :
            raise RuntimeError("u and v must be same length!")
            
        # Generate a set of pixels
        x,y = np.mgrid[limits[0]:limits[1]:shape[0]*1j,limits[2]:limits[3]:shape[1]*1j]
        # Generate a set of intensities (Jy/uas^2)
        I = self.img.intensity_map(x,y,p,verbosity=verbosity)
        V00_img = np.sum(I*np.abs((x[1,1]-x[0,0])*(y[1,1]-y[0,0])))

        uas2rad = np.pi/180./3600e6
        x = x * uas2rad
        y = y * uas2rad
        
        # Generate the complex visibilities, gridded
        V2d = np.fft.fftshift(np.conj(np.fft.fft2(I,s=padding*np.array(shape))))
        u1d = np.fft.fftshift(np.fft.fftfreq(padding*I.shape[0],np.abs(x[1,1]-x[0,0])))
        v1d = np.fft.fftshift(np.fft.fftfreq(padding*I.shape[1],np.abs(y[1,1]-y[0,0])))
        
        # Center image
        i2d,j2d = np.meshgrid(np.arange(V2d.shape[0]),np.arange(V2d.shape[1]))
        V2d = V2d * np.exp(1.0j*np.pi*(i2d+j2d))
        
        
        # Generate the interpolator and interpolate to the u,v list
        Vrinterp = si.RectBivariateSpline(u1d,v1d,np.real(V2d))
        Viinterp = si.RectBivariateSpline(u1d,v1d,np.imag(V2d))

        V00_fft = Vrinterp(0.0,0.0)
        V2d = V2d * V00_img/V00_fft
        
        V = 0.0j * u
        for i in range(len(u)) :
            V[i] = (Vrinterp(u[i],v[i]) + 1.0j*Viinterp(u[i],v[i]))

        return V
            
    def visibility_gradients(self,u,v,p,h=1e-2,limits=None,shape=None,padding=4,verbosity=0) :
        """
        Generates visibilities associated with a given model image object.  Note 
        that this uses FFTs to create the visibilities and then interpolates.

        Args:
          u (np.array): list of u positions in units of :math:`\\lambda`.
          v (np.array): list of v positions in units of :math:`\\lambda`.
          p (np.array): list of parameters for the model image used to create object.
          h (float): fractional step for finite-difference gradient computation.  Default: 0.01.
          limits (list): May be single number, list with four elements specifying in :math:`\\mu as` the symmetric limits or explicit limits in [xmin,xmax,ymin,ymax] order.  Default: 100.
          shape (list): May be single number or list with two elements indicating the number of pixels in the two directions.  Default: 256.
          padding (int): Factor by which to pad image with zeros prior to FFT.  Default: 4.
          verbosity (int): Verbosity level. 0 prints nothing. 1 prints various elements of the plotting process. Passed to :func:`model_image.generate_intensity_map`. Default: 0.

        Returns:
          gradV (np.ndarray): list of complex visibilities gradients computed at u,v.
        """

        pp = np.copy(p)
        gradV = np.zeros((len(u),self.img.size))
        
        for i in range(self.img.size) :
            if (np.abs(p[i])>0) :
                hq = h*np.abs(p[i])
            else :
                hq = h**2
            pp[i] = p[i] + hq
            Vmp = np.copy(self.visibilities(u,v,pp,limits=limits,shape=shape,padding=padding,verbosity=verbosity))
            pp[i] = p[i] - hq
            Vmm = np.copy(self.visibilities(u,v,pp,limits=limits,shape=shape,padding=padding,verbosity=verbosity))
            pp[i] = p[i]
            gradV[:,i] = (Vmp-Vmm)/(2.0*hq)

        return gradV

    def parameter_labels(self) :
        return self.img.parameter_name_list()
    

class FF_smoothed_delta_ring(FisherForecast) :

    def __init__(self) :
        super().__init__()
        self.size = 3
        
    def visibilities(self,u,v,p,verbosity=0) :
        # Takes:
        #  p[0] ... flux in Jy
        #  p[1] ... diameter in uas
        #  p[2] ... width in uas

        d = p[1]
        w = p[2] 
        uas2rad = np.pi/180./3600e6
        piuv = np.pi*np.sqrt(u**2+v**2)*uas2rad
        x = piuv*d
        y = piuv*w
        J0 = ss.jv(0,x)
        J1 = ss.jv(1,x)
        ey2 = np.exp(-0.5*y**2)
        V = p[0] * J0 * ey2
        return V
        
    def visibility_gradients(self,u,v,p,verbosity=0) :
        # Takes:
        #  p[0] ... flux in Jy
        #  p[1] ... diameter in uas
        #  p[2] ... width in uas

        d = p[1]
        w = p[2]
        uas2rad = np.pi/180./3600e6
        piuv = np.pi*np.sqrt(u**2+v**2)*uas2rad
        x = piuv*d
        y = piuv*w
        J0 = ss.jv(0,x)
        J1 = ss.jv(1,x)
        ey2 = np.exp(-0.5*y**2)

        gradV = np.array([ J0*ey2,  # dV/dp[0]
                           -p[0]*piuv*J1*ey2, # dV/dd
                           -p[0]*piuv**2*w*J0*ey2 ]) # dV/dw

        return gradV.T
        

    def parameter_labels(self) :
        return [r'$\delta F~({\rm Jy})$',r'$\delta d~(\mu{\rm as})$',r'$\delta w~(\mu{\rm as})$']
    

class FF_symmetric_gaussian(FisherForecast) :

    def __init__(self) :
        super().__init__()
        self.size = 2
        
    def visibilities(self,u,v,p,verbosity=0) :
        # Takes:
        #  p[0] ... flux in Jy
        #  p[1] ... diameter in uas

        d = p[1]
        uas2rad = np.pi/180./3600e6
        piuv = 2.0*np.pi*np.sqrt(u**2+v**2)*uas2rad / np.sqrt(8.0*np.log(2.0))
        y = piuv * d
        ey2 = np.exp(-0.5*y**2)
        return p[0]*ey2
        
    def visibility_gradients(self,u,v,p,verbosity=0) :
        # Takes:
        #  p[0] ... flux in Jy
        #  p[1] ... diameter in uas

        d = p[1]
        uas2rad = np.pi/180./3600e6
        piuv = 2.0*np.pi*np.sqrt(u**2+v**2)*uas2rad / np.sqrt(8.0*np.log(2.0))
        y = piuv * d
        ey2 = np.exp(-0.5*y**2)

        gradV = np.array([ ey2, # dV/dp[0]
                           -p[0]*piuv**2*d*ey2 ]) # dV/dd

        return gradV.T
        

    def parameter_labels(self) :
        return [r'$\delta F~({\rm Jy})$',r'$\delta \sigma~(\mu{\rm as})$']


class FF_splined_raster(FisherForecast) :

    def __init__(self,N,fov) :
        super().__init__()
        self.npx = N
        self.size = self.npx**2
        fov = fov * np.pi/(3600e6*180) * (N-1)/N
        
        self.xcp,self.ycp = np.meshgrid(np.linspace(-0.5*fov,0.5*fov,self.npx),np.linspace(-0.5*fov,0.5*fov,self.npx))

        self.apx = (self.xcp[1,1]-self.xcp[0,0])*(self.ycp[1,1]-self.ycp[0,0])

    def visibilities(self,u,v,p,verbosity=0) :
        # Takes:
        #  p[0] ... p[0,0]
        #  p[1] ... p[1,0]
        #  ...
        #  p[NxN-1] = p[N-1,N-1]

        V = 0.0j*u
        
        # Add themage
        for i in range(self.npx) :
            for j in range(self.npx) :
                V = V + np.exp(-2.0j*np.pi*(u*self.xcp[i,j]+v*self.ycp[i,j]) + p[i+self.npx*j]) * ty.vis.W_cubic_spline_1d(2.0*np.pi*self.xcp[i,j]*u)*ty.vis.W_cubic_spline_1d(2.0*np.pi*self.ycp[i,j]*v) * self.apx
        
        return V
        
    def visibility_gradients(self,u,v,p,verbosity=0) :
        # Takes:
        #  p[0] ... p[0,0]
        #  p[1] ... p[1,0]
        #  ...
        #  p[NxN-1] = p[N-1,N-1]

        gradV = []

        # Add themage
        for j in range(self.npx) :
            for i in range(self.npx) :
                gradV.append( np.exp(-2.0j*np.pi*(u*self.xcp[i,j]+v*self.ycp[i,j]) + p[i+self.npx*j]) * ty.vis.W_cubic_spline_1d(2.0*np.pi*self.xcp[i,j]*u)*ty.vis.W_cubic_spline_1d(2.0*np.pi*self.ycp[i,j]*v) * self.apx )

        gradV = np.array(gradV)
        
        return gradV.T
        

    def parameter_labels(self) :

        pll = []
        for j in range(self.npx) :
            for i in range(self.npx) :
                pll.append( r'$\delta I_{%i,%i}$'%(i,j) )

        return pll


class FF_smoothed_delta_ring_themage(FisherForecast) :

    def __init__(self,N,fov) :
        super().__init__()
        self.npx = N
        self.size = self.npx**2 + 3
        fov = fov * np.pi/(3600e6*180) * (N-1)/N
        
        self.xcp,self.ycp = np.meshgrid(np.linspace(-0.5*fov,0.5*fov,self.npx),np.linspace(-0.5*fov,0.5*fov,self.npx))

        self.apx = (self.xcp[1,1]-self.xcp[0,0])*(self.ycp[1,1]-self.ycp[0,0])

    def visibilities(self,u,v,p,verbosity=0) :
        # Takes:
        #  p[0] ... p[0,0]
        #  p[1] ... p[1,0]
        #  ...
        #  p[NxN-1] = p[N-1,N-1]
        #  p[NxN+0] ... ring flux in Jy
        #  p[NxN+1] ... ring diameter in uas
        #  p[NxN+2] ... ring width in uas

        V = 0.0j*u

        # print("p:",p)
        
        # Add themage
        for i in range(self.npx) :
            for j in range(self.npx) :
                V = V + np.exp(-2.0j*np.pi*(u*self.xcp[i,j]+v*self.ycp[i,j]) + p[i+self.npx*j]) * ty.vis.W_cubic_spline_1d(2.0*np.pi*self.xcp[i,j]*u)*ty.vis.W_cubic_spline_1d(2.0*np.pi*self.ycp[i,j]*v) * self.apx

        # print(u[:5],v[:5],V[:5])

                
        # Add ring
        d = p[-2]
        w = p[-1]
        uas2rad = np.pi/180./3600e6
        piuv = np.pi*np.sqrt(u**2+v**2)*uas2rad
        x = piuv*d
        y = piuv*w
        J0 = ss.jv(0,x)
        J1 = ss.jv(1,x)
        ey2 = np.exp(-0.5*y**2)
        V = V + p[-3] * J0 * ey2
        
        return V
        
    def visibility_gradients(self,u,v,p,verbosity=0) :
        # Takes:
        #  p[0] ... p[0,0]
        #  p[1] ... p[1,0]
        #  ...
        #  p[NxN-1] = p[N-1,N-1]
        #  p[NxN+0] ... ring flux in Jy
        #  p[NxN+1] ... ring diameter in uas
        #  p[NxN+2] ... ring width in uas

        gradV = []

        # Add themage
        for j in range(self.npx) :
            for i in range(self.npx) :
                gradV.append( np.exp(-2.0j*np.pi*(u*self.xcp[i,j]+v*self.ycp[i,j]) + p[i+self.npx*j]) * ty.vis.W_cubic_spline_1d(2.0*np.pi*self.xcp[i,j]*u)*ty.vis.W_cubic_spline_1d(2.0*np.pi*self.ycp[i,j]*v) * self.apx )
        
        # Add ring
        d = p[-2]
        w = p[-1]
        uas2rad = np.pi/180./3600e6
        piuv = np.pi*np.sqrt(u**2+v**2)*uas2rad
        x = piuv*d
        y = piuv*w
        J0 = ss.jv(0,x)
        J1 = ss.jv(1,x)
        ey2 = np.exp(-0.5*y**2)

        gradV.append( J0*ey2 ) # dV/dF
        gradV.append( -p[-3]*piuv*J1*ey2 ) # dV/dd
        gradV.append( -p[-3]*piuv**2*w*J0*ey2 ) # dV/dw

        gradV = np.array(gradV)
        
        # print("FOO:",gradV.shape)
        
        return gradV.T
        

    def parameter_labels(self) :

        pll = []
        for j in range(self.npx) :
            for i in range(self.npx) :
                pll.append( r'$\delta I_{%i,%i}$'%(i,j) )

        pll.append(r'$\delta F~({\rm Jy})$')
        pll.append(r'$\delta d~(\mu{\rm as})$')
        pll.append(r'$\delta w~(\mu{\rm as})$')

        return pll



    
class FF_sum(FisherForecast) :

    def __init__(self,ff_list=None) :
        super().__init__()
        self.ff_list = []

        if (not ff_list is None) :
            self.ff_list = copy.copy(ff_list) # This is a SHALLOW copy

        self.size=0
        if (not ff_list is None) :
            self.size = ff_list[0].size
            for ff in self.ff_list[1:] :
                self.size += ff.size+2
                

    def add(self,ff) :
        self.ff_list.append(ff)
        if (len(self.ff_list)==1) :
            self.size += ff.size
        else :
            self.size += ff.size+2
            
    def visibilities(self,u,v,p,verbosity=0) :
        V = 0.0j*u
        k = 0
        uas2rad = np.pi/180./3600e6        
        for i,ff in enumerate(self.ff_list) :
            q = p[k:(k+ff.size)]

            if (i==0) :
                shift_factor = 1.0
                k += ff.size
            else :
                dx = p[k+ff.size]
                dy = p[k+ff.size+1]
                shift_factor = np.exp( 2.0j*np.pi*(u*dx+v*dy)*uas2rad )
                k += ff.size + 2
                
            V = V + ff.visibilities(u,v,q,verbosity=verbosity) * shift_factor
        return V

    def visibility_gradients(self,u,v,p,verbosity=0) :
        gradV = []
        k = 0
        uas2rad = np.pi/180./3600e6        
        for i,ff in enumerate(self.ff_list) :
            q = p[k:(k+ff.size)]
            dx = p[k+ff.size]
            dy = p[k+ff.size+1]

            if (i==0) :
                shift_factor = 1.0
                k += ff.size
            else :
                dx = p[k+ff.size]
                dy = p[k+ff.size+1]
                V = ff.visibilities(u,v,q,verbosity=verbosity)
                shift_factor = np.exp( -2.0j*np.pi*(u*dx+v*dy)*uas2rad )
                k += ff.size + 2
            
            for gV in ff.visibility_gradients(u,v,q,verbosity=verbosity).T :
                gradV.append( gV*shift_factor )

            if (i>0) :
                gradV.append(-2.0j*np.pi*u*shift_factor*V*uas2rad)
                gradV.append(-2.0j*np.pi*v*shift_factor*V*uas2rad)

        gradV = np.array(gradV)

        # print("gradV size:",gradV.shape)
        
        return gradV.T
                
    def parameter_labels(self) :

        pll = []
        for i,ff in enumerate(self.ff_list) :
            for lbl in ff.parameter_labels() :
                pll.append(lbl)
            if (i>0) :
                pll.append(r'$\delta\Delta x~(\mu{\rm as})$')
                pll.append(r'$\delta\Delta y~(\mu{\rm as})$')
        
        return pll


            

    


_ff_color_list = ['r','b','g','orange','purple']
_ff_cmap_list = ['Reds_r','Blues_r','Greens_r','Oranges_r','Purples_r']
_ff_color_size = 5
    
def plot_1d_forecast(ff,p,i1,obslist,labels=None) :

    if (labels is None) :
        labels = len(obslist)*[None]
    
    plt.figure(figsize=(5,4))
    plt.axes([0.15,0.15,0.8,0.8])
    
    n = 256
    
    sigdict = {}
    for k,obs in enumerate(obslist) :
        _,Sigm = ff.uncertainties_from_obs(obs,p)

        x = np.linspace(-5*Sigm[i1],5*Sigm[i1],n)
        y = np.exp(-x**2/(2.0*Sigm[i1]**2)) / np.sqrt(2.0*np.pi*Sigm[i1]**2)

        plt.fill_between(x,y,y2=0,alpha=0.25,color=_ff_color_list[k%_ff_color_size])
        plt.plot(x,y,'-',color=_ff_color_list[k%_ff_color_size],label=labels[k])

    plt.xlabel(ff.parameter_labels()[i1])
    plt.yticks([])
    plt.ylim(bottom=0)
    plt.legend()

    return plt.gcf(),plt.gca()


def plot_2d_forecast(ff,p,i1,i2,obslist,labels=None) :
    
    if (labels is None) :
        labels = len(obslist)*[None]

    plt.figure(figsize=(5,5))
    plt.axes([0.2,0.2,0.75,0.75])

    for k,obs in enumerate(obslist) :
        d,w,csq,mcsq = ff.joint_biparameter_chisq(obs,p,i1,i2)
        plt.contourf(d,w,np.sqrt(mcsq),cmap=_ff_cmap_list[k%_ff_color_size],alpha=0.75,levels=[0,1,2,3])
        plt.contour(d,w,np.sqrt(mcsq),colors=_ff_color_list[k%_ff_color_size],alpha=1,levels=[0,1,2,3])
        plt.plot([],[],'-',color=_ff_color_list[k%_ff_color_size],label=labels[k])
    
    plt.xlabel(ff.parameter_labels()[i1])
    plt.ylabel(ff.parameter_labels()[i2])
    plt.grid(True,alpha=0.25)
    plt.legend()

    return plt.gcf(),plt.gca()


def plot_triangle_forecast(ff,p,ilist,obslist,labels=None) :

    wdx = 2
    wdy = 2
    wgx = 0.25
    wgy = 0.25
    wmx = 1
    wmy = 0.75

    ni = len(ilist)

    fx = wmx + ni*(wdx+wgx)
    fy = wmy + ni*(wdy+wgy)

    
    plt.figure(figsize=(fx,fy))
    axs = {}
    for i in range(ni) :
        for j in range(ni-i) :
            ax0 = wmx + i*(wdx+wgx)
            ay0 = wmy + j*(wdy+wgy)
            axs[i,j] = plt.axes([ax0/fx,ay0/fy,wdx/fx,wdy/fy])

    xlim_dict = {}
    for k,obs in enumerate(obslist) :
        _,Sigm = ff.uncertainties_from_obs(obs,p)

        for j in range(ni) :
            jj = ilist[j]
            xtmp = np.linspace(-3.5*Sigm[jj],3.5*Sigm[jj],256)
            ytmp = np.exp(-xtmp**2/(2.0*Sigm[jj]**2))/np.sqrt(2.0*np.pi*Sigm[jj]**2)
            axs[j,ni-j-1].fill_between(xtmp,ytmp,y2=0,color=_ff_color_list[k%_ff_color_size],alpha=0.25)
            axs[j,ni-j-1].plot(xtmp,ytmp,color=_ff_color_list[k%_ff_color_size])

            if (k==0) :
                xlim_dict[j] = (-3.5*Sigm[jj],3.5*Sigm[jj])
            else :
                if (3.5*Sigm[jj]>xlim_dict[j][1]) :
                    xlim_dict[j] = (-3.5*Sigm[jj],3.5*Sigm[jj])                    
                
        for i in range(ni) :
            for j in range(ni-i-1) :
                ii = ilist[i]
                jj = ilist[ni-j-1]

                plt.sca(axs[i,j])
        
                p1,p2,csq,mcsq = ff.joint_biparameter_chisq(obs,p,ii,jj)
                plt.contourf(p1,p2,np.sqrt(mcsq),cmap=_ff_cmap_list[k%_ff_color_size],alpha=0.75,levels=[0,1,2,3])
                plt.contour(p1,p2,np.sqrt(mcsq),colors=_ff_color_list[k%_ff_color_size],alpha=1,levels=[0,1,2,3])

                plt.xlim(xlim_dict[i])
                plt.ylim(xlim_dict[ni-j-1])

                plt.grid(True,alpha=0.25)


    for j in range(ni) :
        axs[j,ni-j-1].set_xlim(xlim_dict[j])
        axs[j,ni-j-1].set_ylim(bottom=0)
        axs[j,ni-j-1].set_yticks([])

    for i in range(ni) :
        for j in range(1,ni-i) :
            axs[i,j].set_xticklabels([])
            
    for i in range(1,ni) :
        for j in range(ni-i-1) :
            axs[i,j].set_yticklabels([])

    for j in range(ni-1) :
        axs[0,j].set_ylabel(ff.parameter_labels()[ilist[ni-j-1]])
        
    for i in range(ni) :
        axs[i,0].set_xlabel(ff.parameter_labels()[ilist[i]])


    # Make axis for labels
    if (not labels is None) :
        plt.axes([0.95,0.95,0.01,0.01])
        for k in range(len(obslist)) :
            plt.plot([],[],_ff_color_list[k%_ff_color_size],label=labels[k])
        plt.gca().spines.right.set_visible(False)
        plt.gca().spines.left.set_visible(False)
        plt.gca().spines.top.set_visible(False)
        plt.gca().spines.bottom.set_visible(False)
        plt.gca().set_xticks([])
        plt.gca().set_yticks([])
        plt.legend(loc='upper right',bbox_to_anchor=(0,0))

        
    return plt.gcf(),axs


if __name__ == "__main__" :

    # Example
    
    # Make Fisher forecast object
    ff1 = FF_splined_raster(5,60)
    ff2 = FF_smoothed_delta_ring()
    ff = FF_sum([ff1,ff2])

    # Read in some data
    obs_ngeht = eh.obsdata.load_uvfits('../data/M87_230GHz_40uas.uvfits')
    obs_ngeht.add_scans()
    obs_ngeht = obs_ngeht.avg_coherent(0,scan_avg=True)
    obs_ngeht = obs_ngeht.add_fractional_noise(0.01)
    #
    obs = obs_ngeht.flag_sites(['ALMA','APEX','JCMT','SMA','SMT','LMT','SPT','PV','PDB','KP'])


    obslist = [obs,obs_ngeht]
    labels = ['ngEHT w/o EHT','Full ngEHT']
    
    
    # Choose a default image
    p = np.zeros(ff.size)
    rad2uas = 3600e6*180/np.pi
    for j in range(ff1.npx) :
        for i in range(ff1.npx) :
            p[i+ff1.npx*j] =  -((ff1.xcp[i,j]-5.0/rad2uas)**2+ff1.ycp[i,j]**2)*rad2uas**2/(2.0*25.0**2) + np.log( 1.0/( 2.0*np.pi * (25.0/rad2uas)**2 ) )
    p[-5] = 0.2
    p[-4] = 40
    p[-3] = 2
    p[-2] = 0
    p[-1] = 0
    p = np.array(p)

    # 1D Diameter
    plot_1d_forecast(ff,p,ff.size-4,obslist,labels=labels)
    plt.savefig('ring_forecast_1d.png',dpi=300)

    # 2D diameter vs width
    plot_2d_forecast(ff,p,ff.size-4,ff.size-3,obslist,labels=labels)
    plt.savefig('ring_forecast_2d.png',dpi=300)

    # Triangle
    plist = np.arange(len(p)-5,len(p))
    plot_triangle_forecast(ff,p,plist,obslist,labels=labels)
    plt.savefig('ring_forecast_tri.png',dpi=300)
    
    # plt.show()

