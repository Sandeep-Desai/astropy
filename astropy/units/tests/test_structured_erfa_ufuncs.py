# coding: utf-8
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Test Structured units and quantities specifically with the ERFA ufuncs.
"""
import pytest
import numpy as np
from numpy.testing import assert_array_equal
from erfa import ufunc as erfa_ufunc

from astropy import units as u
from astropy.tests.helper import assert_quantity_allclose


class TestPVUfuncs:
    def setup_class(self):
        self.pv_unit = u.Unit('AU,AU/day')
        self.pv_value = np.array([([1., 0., 0.], [0., 0.0125, 0.]),
                                  ([0., 1., 0.], [-.0125, 0., 0.])],
                                 dtype=erfa_ufunc.dt_pv)
        self.pv = self.pv_value << self.pv_unit

    def test_cpv(self):
        pv_copy = erfa_ufunc.cpv(self.pv)
        assert_array_equal(pv_copy, self.pv)
        assert not np.may_share_memory(pv_copy, self.pv)

    def test_p2pv(self):
        p2pv = erfa_ufunc.p2pv(self.pv['p'])
        assert_array_equal(p2pv['p'], self.pv['p'])
        assert_array_equal(p2pv['v'], np.zeros(self.pv.shape+(3,), float) << u.m/u.s)

    @pytest.mark.xfail(reason='erfa bug; https://github.com/liberfa/pyerfa/issues/70)')
    def test_p2pv_inplace(self):
        # TODO: fix np.zeros_like.
        out = np.zeros_like(self.pv_value) << self.pv_unit
        p2pv = erfa_ufunc.p2pv(self.pv['p'], out=out)
        assert out is p2pv
        assert_array_equal(p2pv['p'], self.pv['p'])
        assert_array_equal(p2pv['v'], np.zeros(self.pv.shape+(3,), float) << u.m/u.s)

    def test_pv2p(self):
        p = erfa_ufunc.pv2p(self.pv)
        assert_array_equal(p, self.pv['p'])
        out = np.zeros_like(p)
        p2 = erfa_ufunc.pv2p(self.pv, out=out)
        assert out is p2
        assert_array_equal(p2, self.pv['p'])

    def test_pv2s(self):
        theta, phi, r, td, pd, rd = erfa_ufunc.pv2s(self.pv)
        assert theta.unit == u.radian
        assert_quantity_allclose(theta, [0, 90] * u.deg)  # longitude
        assert phi.unit == u.radian
        assert_array_equal(phi.value, np.zeros(self.pv.shape))  # latitude
        assert r.unit == u.AU
        assert_array_equal(r.value, np.ones(self.pv.shape))
        assert td.unit == u.radian/u.day
        assert_array_equal(td.value, np.array([0.0125]*2))
        assert pd.unit == u.radian/u.day
        assert_array_equal(pd.value, np.zeros(self.pv.shape))
        assert rd.unit == u.AU/u.day
        assert_array_equal(rd.value, np.zeros(self.pv.shape))

    def test_s2pv(self):
        theta, phi, r, td, pd, rd = erfa_ufunc.pv2s(self.pv)
        # On purpose change some of the units away from expected by s2pv.
        pv = erfa_ufunc.s2pv(theta.to(u.deg), phi, r.to(u.m),
                             td.to(u.deg/u.day), pd, rd.to(u.m/u.s))
        assert pv.unit == u.StructuredUnit('m, m/s', names=('p', 'v'))
        assert_quantity_allclose(pv['p'], self.pv['p'], atol=1*u.m)
        assert_quantity_allclose(pv['v'], self.pv['v'], atol=1*u.mm/u.s)

    def test_pvstar(self):
        ra, dec, pmr, pmd, px, rv, stat = erfa_ufunc.pvstar(self.pv)
        assert_array_equal(stat, np.zeros(self.pv.shape, dtype='i4'))
        assert ra.unit == u.radian
        assert_quantity_allclose(ra, [0, 90] * u.deg)
        assert dec.unit == u.radian
        assert_array_equal(dec.value, np.zeros(self.pv.shape))  # latitude
        assert pmr.unit == u.radian/u.year
        assert_quantity_allclose(pmr, [0.0125, 0.0125]*u.radian/u.day)
        assert pmd.unit == u.radian/u.year
        assert_array_equal(pmd.value, np.zeros(self.pv.shape))
        assert px.unit == u.arcsec
        assert_quantity_allclose(px, 1*u.radian)
        assert rv.unit == u.km / u.s
        assert_array_equal(rv.value, np.zeros(self.pv.shape))

    def test_starpv(self):
        ra, dec, pmr, pmd, px, rv, stat = erfa_ufunc.pvstar(self.pv)
        pv, stat = erfa_ufunc.starpv(ra.to(u.deg), dec.to(u.deg), pmr, pmd,
                                     px, rv.to(u.m/u.s))
        assert_array_equal(stat, np.zeros(self.pv.shape, dtype='i4'))
        assert pv.unit == self.pv.unit
        assert_quantity_allclose(pv['p'], self.pv['p'], atol=1*u.m)
        assert_quantity_allclose(pv['v'], self.pv['v'], atol=1*u.mm/u.s)

    def test_pvtob(self):
        pv = erfa_ufunc.pvtob([90, 0]*u.deg, 0.*u.deg, 100*u.km,
                              0*u.deg, 0*u.deg, 0*u.deg, 90*u.deg)
        assert pv.unit == u.StructuredUnit('m, m/s', names=('p', 'v'))
        assert pv.unit['v'] == u.m / u.s
        assert_quantity_allclose(pv['p'], [[-6478, 0, 0], [0, 6478, 0]]*u.km,
                                 atol=2*u.km)
        assert_quantity_allclose(pv['v'], [[0, -0.5, 0], [-0.5, 0, 0]]*u.km/u.s,
                                 atol=0.1*u.km/u.s)

    def test_pvdpv(self):
        pvdpv = erfa_ufunc.pvdpv(self.pv, self.pv)
        assert pvdpv['pdp'].unit == self.pv.unit['p'] ** 2
        assert pvdpv['pdv'].unit == self.pv.unit['p'] * self.pv.unit['v']
        assert_array_equal(pvdpv['pdp'], np.einsum('...i,...i->...',
                                                   self.pv['p'], self.pv['p']))
        assert_array_equal(pvdpv['pdv'], 2*np.einsum('...i,...i->...',
                                                     self.pv['p'], self.pv['v']))
        z_axis = u.StructuredQuantity(
            np.array(([0, 0, 1], [0, 0, 0]), erfa_ufunc.dt_pv),
            '1,1/s')
        pvdpv2 = erfa_ufunc.pvdpv(self.pv, z_axis)
        assert pvdpv2['pdp'].unit == self.pv.unit['p']
        assert pvdpv2['pdv'].unit == self.pv.unit['v']
        assert_array_equal(pvdpv2['pdp'].value, np.zeros(self.pv.shape))
        assert_array_equal(pvdpv2['pdv'].value, np.zeros(self.pv.shape))

    def test_pvxpv(self):
        pvxpv = erfa_ufunc.pvxpv(self.pv, self.pv)
        assert pvxpv['p'].unit == self.pv.unit['p'] ** 2
        assert pvxpv['v'].unit == self.pv.unit['p'] * self.pv.unit['v']
        assert_array_equal(pvxpv['p'].value, np.zeros(self.pv['p'].shape))
        assert_array_equal(pvxpv['v'].value, np.zeros(self.pv['v'].shape))
        z_axis = u.StructuredQuantity(
            np.array(([0, 0, 1], [0, 0, 0]), erfa_ufunc.dt_pv),
            '1,1/s')
        pvxpv2 = erfa_ufunc.pvxpv(self.pv, z_axis)
        assert pvxpv2['p'].unit == self.pv.unit['p']
        assert pvxpv2['v'].unit == self.pv.unit['v']
        assert_array_equal(pvxpv2['p'], [[0., -1, 0.],
                                         [1., 0., 0.]] * u.AU)
        assert_array_equal(pvxpv2['v'], [[0.0125, 0., 0.],
                                         [0., 0.0125, 0.]] * u.AU / u.day)

    def test_pvm(self):
        pm, vm = erfa_ufunc.pvm(self.pv)
        assert pm.unit == self.pv.unit['p']
        assert vm.unit == self.pv.unit['v']
        assert_array_equal(pm, np.linalg.norm(self.pv['p'], axis=-1))
        assert_array_equal(vm, np.linalg.norm(self.pv['v'], axis=-1))

    def test_pvmpv(self):
        pvmpv = erfa_ufunc.pvmpv(self.pv, self.pv)
        assert pvmpv.unit == self.pv.unit
        assert_array_equal(pvmpv['p'], 0*self.pv['p'])
        assert_array_equal(pvmpv['v'], 0*self.pv['v'])

    def test_pvppv(self):
        pvppv = erfa_ufunc.pvppv(self.pv, self.pv)
        assert pvppv.unit == self.pv.unit
        assert_array_equal(pvppv['p'], 2*self.pv['p'])
        assert_array_equal(pvppv['v'], 2*self.pv['v'])

    def test_pvu(self):
        pvu = erfa_ufunc.pvu(86400*u.s, self.pv)
        assert pvu.unit == self.pv.unit
        assert_array_equal(pvu['p'], self.pv['p'] + 1*u.day*self.pv['v'])
        assert_array_equal(pvu['v'], self.pv['v'])

    def test_pvup(self):
        pvup = erfa_ufunc.pvup(86400*u.s, self.pv)
        assert pvup.unit == self.pv.unit['p']
        assert_array_equal(pvup, self.pv['p'] + 1*u.day*self.pv['v'])

    def test_sxpv(self):
        # Not a realistic example!!
        sxpv = erfa_ufunc.sxpv(10., self.pv)
        assert sxpv.unit == self.pv.unit
        assert_array_equal(sxpv['p'], self.pv['p']*10)
        assert_array_equal(sxpv['v'], self.pv['v']*10)
        sxpv2 = erfa_ufunc.sxpv(30.*u.s, self.pv)
        assert sxpv2.unit == u.StructuredUnit('AU s,AU s/d', names=('p', 'v'))
        assert_array_equal(sxpv2['p'], self.pv['p']*30*u.s)
        assert_array_equal(sxpv2['v'], self.pv['v']*30*u.s)

    def test_s2xpv(self):
        # Not a realistic example!!
        s2xpv = erfa_ufunc.s2xpv(10., 1*u.s, self.pv)
        assert s2xpv.unit == u.StructuredUnit('AU,AU s/d', names=('p', 'v'))
        assert_array_equal(s2xpv['p'], self.pv['p']*10)
        assert_array_equal(s2xpv['v'], self.pv['v']*u.s)

    @pytest.mark.parametrize('r', [
        np.eye(3),
        np.array([[0., -1., 0.],
                  [1., 0., 0.],
                  [0., 0., 1.]]),
        np.eye(3) / u.s])
    def test_rxpv(self, r):
        result = erfa_ufunc.rxpv(r, self.pv)
        assert_array_equal(result['p'], np.einsum('...ij,...j->...i',
                                                  r, self.pv['p']))
        assert_array_equal(result['v'], np.einsum('...ij,...j->...i',
                                                  r, self.pv['v']))

    @pytest.mark.parametrize('r', [
        np.eye(3),
        np.array([[0., -1., 0.],
                  [1., 0., 0.],
                  [0., 0., 1.]]),
        np.eye(3) / u.s])
    def test_trxpv(self, r):
        result = erfa_ufunc.trxpv(r, self.pv)
        assert_array_equal(result['p'], np.einsum('...ij,...j->...i',
                                                  r.T, self.pv['p']))
        assert_array_equal(result['v'], np.einsum('...ij,...j->...i',
                                                  r.T, self.pv['v']))
