"""Tests of the Traffic class"""

import unittest
import yaml

from fibertree import Metrics, Tensor
from fibertree.model import Format, Traffic

class TestTraffic(unittest.TestCase):
    """Tests of the Traffic class"""

    def setUp(self):
        K = 8
        M = 6
        N = 7
        density = 0.5
        # Create the tensors
        A_KM = Tensor.fromRandom(
            rank_ids=[
                "K", "M"], shape=[
                K, M], density=[
                    0.9, density], seed=0)
        self.B_KN = Tensor.fromRandom(
            rank_ids=[
                "K", "N"], shape=[
                K, N], density=[
                    0.9, density], seed=1)
        self.A_MK = A_KM.swizzleRanks(rank_ids=["M", "K"])

        b_k = self.B_KN.getRoot()
        a_m = self.A_MK.getRoot()
        T_MKN = Tensor(rank_ids=["M", "K", "N"])
        t_m = T_MKN.getRoot()

        Metrics.beginCollect("tmp/test_traffic_stage0")
        Metrics.trace("M")
        Metrics.trace("K")
        Metrics.trace("K", type_="intersect_2_3")
        for m, (t_k, a_k) in t_m << a_m:
            for k, (t_n, (a_val, b_n)) in t_k << (a_k & b_k):
                for n, (t_ref, b_val) in t_n << b_n:
                    t_ref += b_val
        Metrics.endCollect()

        a_m = self.A_MK.getRoot()
        self.T_MNK = T_MKN.swizzleRanks(rank_ids=["M", "N", "K"])
        t_m = self.T_MNK.getRoot()
        self.Z_MN = Tensor(rank_ids=["M", "N"])
        z_m = self.Z_MN.getRoot()

        Metrics.beginCollect("tmp/test_traffic_stage1")
        Metrics.trace("N")
        for m, (z_n, (t_n, a_k)) in z_m << (t_m & a_m):
            for n, (z_ref, t_k) in z_n << t_n:
                for k, (t_val, a_val) in t_k & a_k:
                    z_ref += t_val * a_val
        Metrics.endCollect()

        formats = yaml.safe_load("""
        B:
            K:
                format: U
                rhbits: 32
                pbits: 32
            N:
                format: C
                cbits: 32
                pbits: 64
        T:
            M:
                format: U
                pbits: 32
            N:
                format: C
                rhbits: 256
                fhbits: 128
                cbits: 32
                pbits: 64
            K:
                format: C
                pbits: 64
        """)

        self.B_format = Format(self.B_KN, formats["B"])
        self.T_format = Format(self.T_MNK, formats["T"])

        # We can also have a single-stage version of Gustavson's
        b_k = self.B_KN.getRoot()
        a_m = self.A_MK.getRoot()
        Z_MN = Tensor(rank_ids=["M", "N"])
        z_m = Z_MN.getRoot()

        Metrics.beginCollect("tmp/test_traffic_single_stage")
        Metrics.trace("N", type_="populate_0_1")
        for m, (z_n, a_k) in z_m << a_m:
            for k, (a_val, b_n) in a_k & b_k:
                for n, (z_ref, b_val) in z_n << b_n:
                    z_ref += a_val * b_val
        Metrics.endCollect()

    def test_buildTrace_iter(self):
        """Test buildTrace with trace_type=iter"""
        corrM = [
            "M\n",
            "0\n",
            "1\n",
            "2\n",
            "3\n",
            "4\n",
            "5\n"
        ]

        corrK = [
            "M,K\n",
            "0,1\n",
            "0,7\n",
            "1,0\n",
            "1,5\n",
            "2,1\n",
            "2,6\n",
            "3,0\n",
            "3,2\n",
            "3,5\n",
            "4,2\n",
            "4,6\n",
            "4,7\n",
            "5,0\n",
            "5,6\n"
        ]

        Traffic.buildTrace("M", "tmp/test_traffic_stage0-K-iter.csv", "tmp/test_buildTrace_iter-M.csv")

        with open("tmp/test_buildTrace_iter-M.csv", "r") as f:
            self.assertEqual(f.readlines(), corrM)

        Traffic.buildTrace("K", "tmp/test_traffic_stage0-K-iter.csv", "tmp/test_buildTrace_iter-K.csv")

        with open("tmp/test_buildTrace_iter-K.csv", "r") as f:
            self.assertEqual(f.readlines(), corrK)

    def test_buildTrace_intersect_no_tensor(self):
        """Test buildTrace for an intersection trace without an explicit
        tensor number"""

        with self.assertRaises(AssertionError):
            Traffic.buildTrace("K", "tmp/test_traffic_stage0-K-intersect_2_3.csv", "tmp/bad.csv", trace_type="intersect")

    def test_buildTrace_intersect(self):
        """Test buildTrace with an intersection"""

        corr = [
            "M,K\n",
            "0,1\n",
            "0,7\n",
            "1,0\n",
            "1,5\n",
            "2,1\n",
            "2,6\n",
            "3,0\n",
            "3,2\n",
            "3,5\n",
            "4,2\n",
            "4,6\n",
            "4,7\n",
            "5,0\n",
            "5,6\n"
        ]

        Traffic.buildTrace("K",
            "tmp/test_traffic_stage0-K-intersect_2_3.csv",
            "tmp/test_buildTrace_intersect.csv",
            trace_type="intersect", tensor=2)

        with open("tmp/test_buildTrace_intersect.csv", "r") as f:
            self.assertEqual(f.readlines(), corr)

    def test_buildTrace_populate_no_tensor(self):
        """Test buildTrace for an populate trace without an explicit tensor number"""

        with self.assertRaises(AssertionError):
            Traffic.buildTrace("K", "tmp/test_traffic_single_stage-N-populate_0_1.csv", "tmp/bad.csv", trace_type="populate")

    def test_buildTrace_populate_1(self):
        """Test buildTrace for a populate trace"""
        Traffic.buildTrace(
            "N",
            "tmp/test_traffic_single_stage-N-populate_0_1.csv",
            "tmp/test_buildTrace_populate_1.csv",
            trace_type="populate", tensor=1)

        with open("tmp/test_buildTrace_populate_1.csv", "r") as f_test, \
             open("test_traffic-test_buildTrace_populate-corr1.csv", "r") as f_corr:
            self.assertEqual(f_test.readlines(), f_corr.readlines())

    def test_buildTrace_populate_read0(self):
        """Test buildTrace for a populate trace"""
        Traffic.buildTrace(
            "N",
            "tmp/test_traffic_single_stage-N-populate_0_1.csv",
            "tmp/test_buildTrace_populate_read0.csv",
            trace_type="populate", tensor=0)

        with open("tmp/test_buildTrace_populate_read0.csv", "r") as f_test, \
             open("test_traffic-test_buildTrace_populate-corr0-read.csv", "r") as f_corr:
            self.assertEqual(f_test.readlines(), f_corr.readlines())

    def test_buildTrace_populate_write0(self):
        """Test buildTrace for a populate trace"""
        Traffic.buildTrace(
            "N",
            "tmp/test_traffic_single_stage-N-populate_0_1.csv",
            "tmp/test_buildTrace_populate_write0.csv",
            trace_type="populate", access_type="write", tensor=0)

        with open("tmp/test_buildTrace_populate_write0.csv", "r") as f_test, \
             open("test_traffic-test_buildTrace_populate-corr0-write.csv", "r") as f_corr:
            self.assertEqual(f_test.readlines(), f_corr.readlines())

    def test_buffetTraffic(self):
        """Test buffetTraffic"""
        bits = Traffic.buffetTraffic_old(
            "tmp/test_traffic_stage0", self.B_KN, "K", self.B_format)
        corr = 480 + 288 + 288 + 480 + 480 + 288 + 288 + 96 + 480 + 96 + 288 + 288 + 288 + 288
        self.assertEqual(bits, corr)

    def test_buffetTraffic_fiber(self):
        bits = Traffic.buffetTraffic_old(
            "tmp/test_traffic_stage0", self.B_KN, "M", self.B_format, mode="fiber")
        corr = 6 * 8 * 32
        self.assertEqual(bits, corr)

    def test_cacheTraffic(self):
        """Test cacheTraffic"""
        bits = Traffic.cacheTraffic_old(
            "tmp/test_traffic_stage0", self.B_KN, "K", self.B_format, 2**10)
        corr = 480 + 288 + 288 + 480 +  0 + 288 + 288 + 96 + 0 + 0 + 288 + 288 + 0 + 0
        self.assertEqual(bits, corr)

    def test_lruTraffic(self):
        """Test cacheTraffic"""
        bits = Traffic.lruTraffic_old(
            "tmp/test_traffic_stage0", self.B_KN, "K", self.B_format, 2**10 + 2**8)
        corr = 480 + 288 + 288 + 480 + 480 + 288 + 288 + 96 + 480 + 0 + 0 + 288 + 288 + 0
        self.assertEqual(bits, corr)

    def test_streamTraffic(self):
        """Test streamTraffic"""
        bits = Traffic.streamTraffic_old(
            "tmp/test_traffic_stage1", self.T_MNK, "N", self.T_format)
        corr = 256 + 128 * 6 + (64 + 32) * 33

        self.assertEqual(bits, corr)

    def test_getAllUses(self):
        """Test _getAllUses"""
        uses = [((0, 0, 0), (1, 2, 3)), ((4, 3, 2), (1, 2, 3)),
                ((0, 0, 1), (1, 2, 6)), ((0, 5, 6), (10, 8, 7)),
                ((2, 6, 9), (10, 8, 7)), ((3, 6, 8), (10, 8, 7))]

        with open("tmp/test_getAllUses-K-iter.csv", "w") as f:
            f.write("M_pos,N_pos,K_pos,M,N,K\n")
            for use in uses:
                data = [str(i) for i in use[0] + use[1]]
                f.write(",".join(data) + "\n")

        A_MK = Tensor(rank_ids=["M", "K"])
        result = list(Traffic._getAllUses("tmp/test_getAllUses", A_MK, "K"))
        corr = [(use[1][0], use[1][2]) for use in uses]

        self.assertEqual(result, corr)
