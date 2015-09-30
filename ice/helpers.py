import numpy as np
from scipy import weave

def normvar(img):
    greyimg = np.asarray(img.convert('L'))
    h, w = greyimg.shape

    # Normalised variance
    ccode_normvar = """
        // Calculate mean
        double m = 0.;
        for(int i = 0; i < h; i++) {
            for(int j = 0; j < w; j++) {
                m += greyimg(i, j);
            }
        }
        m /= h*w;
        // Calculate standard deviation
        double thisvar = 0.0;
        for(int i = 0; i < h; i++) {
            for(int j = 0; j < w; j++) {
                thisvar += (greyimg(i, j) - m) * (greyimg(i, j) - m);
            }
        }
        thisvar /= h*w*m;
        return_val = thisvar;

    """
    return weave.inline(
                ccode_normvar,
                ['h', 'w', 'greyimg'],
                type_converters = weave.converters.blitz,
                compiler='gcc'
               )
