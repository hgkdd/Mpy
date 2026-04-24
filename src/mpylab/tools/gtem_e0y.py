"""mpylab.tools.gtem_e0y module."""
import numpy as np
from scipy.special import j0

class GTEM:
    """GTEM class."""
    def __init__(self, az: float, hz: float, gz: float, zz: float, Zc: float = 50) -> None:
        self.az = az
        self.hz = hz
        self.gz = gz
        self.zz = zz
        self.Zc = Zc
        self.points = self.generate_points(zz, 100, 100)

    def a(self, z):
        """a method."""
        return self.az/self.zz * z

    def g(self, z):
        """g method."""
        return self.gz/self.zz * z

    def h(self, z):
        """h method."""
        return self.hz/self.zz * z

    def e0y(self, x, y, z, max_m: int = 1000):
        """e0y method."""
        x = np.asarray(x)
        y = np.asarray(y)
        z = np.asarray(z)

        m = np.arange(1, max_m, 2)[:, None]  # (m,1)

        a = self.a(z)[None, :]  # (1,N)
        h = self.h(z)[None, :]
        g = self.g(z)[None, :]

        M = m * np.pi / a  # (m,N)

        yv = y[None, :]
        xv = x[None, :]

        #denom = 1 - np.exp(-2 * M * h)
        #_coth = (np.exp(-M * (h - yv)) + np.exp(-M * (h + yv))) / denom
        denom = -np.expm1(-2 * M * h)  # = 1 - exp(-2Mh)

        term1 = np.exp(-M * (h - yv))
        term2 = np.exp(-M * (h + yv))
        _coth = (term1 + term2) / denom
        #_coth = np.cosh(M * yv) / np.sinh(M * h)
        _cos = np.cos(M * xv)
        _sin = np.sin(M * 0.5 * a)
        _j0 = j0(M * g)

        _sum = (_coth * _cos * _sin * _j0).sum(axis=0)  # (N,)

        return 4 * np.sqrt(self.Zc) / self.a(z) * _sum  # (N,)

    def generate_points(self, zmax, num_points_z, num_points_xy):
        """
        Generate a 3D array of points ``(x, y, z)`` from chamber geometry.

        Parameters:
            zmax (float): Maximum z coordinate.
            num_points_z (int): Number of samples along the z axis.
            num_points_xy (int): Number of samples for x and y per z slice.

        Returns:
            numpy.ndarray: Array containing points ``(x, y, z)``.
        """
        # Generate z values.
        z_values = np.linspace(zmax/num_points_z, zmax, num_points_z)
        points = []

        for z in z_values:
            # Ranges for x and y based on z.
            x_min, x_max = -self.a(z)/2, self.a(z)/2
            y_min, y_max = 0, self.h(z)

            # Generate x and y values.
            x_values = np.linspace(x_min, x_max, num_points_xy)
            y_values = np.linspace(y_min, y_max, num_points_xy)

            # Build x/y grid.
            x_grid, y_grid = np.meshgrid(x_values, y_values)

            # Combine x, y, z to points.
            for i in range(x_grid.shape[0]):
                for j in range(x_grid.shape[1]):
                    points.append([x_grid[i, j], y_grid[i, j], z])

        return np.array(points)

    def evaluate_function_on_points(self, points, fnc, chunk_size: int = 20000, **kwargs):
        """
        Evaluate a field function on a ``(N, 3)`` point cloud.

        :param points: Input points shaped ``(N, 3)``.
        :param fnc: Function compatible with ``e0y(x, y, z, ...)``.
        :param chunk_size: Number of points processed per chunk.
        :param kwargs: Additional keyword arguments forwarded to ``fnc``.
        """
        x, y, z = points[:, 0], points[:, 1], points[:, 2]
        out = np.empty(x.shape[0], dtype=float)

        for i in range(0, x.shape[0], chunk_size):
            sl = slice(i, min(i + chunk_size, x.shape[0]))
            out[sl] = fnc(x[sl], y[sl], z[sl], **kwargs)

        return out



if __name__ == '__main__':
    cell = GTEM(3.009, 1.5, 0.536, 5.9, Zc=377)
