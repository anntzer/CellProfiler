'''test_morph - test the morphology module

CellProfiler is distributed under the GNU General Public License.
See the accompanying file LICENSE for details.

Developed by the Broad Institute
Copyright 2003-2009

Please see the AUTHORS file for credits.

Website: http://www.cellprofiler.org
'''
__version__ = "$Revision$"

import base64
import numpy as np
import scipy.ndimage as scind
import StringIO
import unittest
import zlib

import cellprofiler.pipeline as cpp
import cellprofiler.cpimage as cpi
import cellprofiler.measurements as cpmeas
import cellprofiler.objects as cpo
import cellprofiler.pipeline as cpp
import cellprofiler.workspace as cpw
import cellprofiler.modules.morph as morph
import cellprofiler.cpmath.cpmorphology as cpmorph

class TestMorph(unittest.TestCase):
    def test_01_01_load_matlab(self):
        '''Load a pipeline that has a morph module in it'''
        #
        # Pipeline has Morph as second module
        # input_name = OrigBlue
        # output_name = MorphBlue
        # dilate once
        # erode twice
        # fill forever
        #
        data = ('eJzzdQzxcXRSMNUzUPB1DNFNy8xJ1VEIyEksScsvyrV'
                'SCHAO9/TTUXAuSk0sSU1RyM+zUggpTVXwKs1TMDBSMDS'
                '0MjKyMjZTMDIwsFQgGTAwevryMzAw/GdkYKiYczfsrtd'
                'hAxG7t7sMWdurVBdd8M7/s/9jkOvBxjzn4w4f1NZF8qa'
                'cfXF+hl1j/2PlHxlqm29f2jFzq7awD+fTJc9/nzs5fbK'
                'JKMOPGGaNj+Uzy4X3RRtu413J/ZuxXfHjnQUcYjlHH8/'
                'fs32C/wXjo7ouyjIHdvQeWx3Xbhpf/di//EynxrqF696'
                'cidZ9ZZdsv6Lc7cCP4mYeg1qFfIlJuU/K+n+rKJzp/mi'
                '438qq77STap7rEQ3/EgMR2Ra92Zd2fLBv79xv6rq99GS'
                '97TtfG47v69lXyN6KFdkWz3J+ZtvyNR84dr8T/j7JW/e'
                'Du9SeqQeiC0ovrjg3+X+XUHnqivn3qwUbVWXFzsa362t'
                'WJFq3LBI4v51vNVfcjfAz3yIy3BnnnXFevnjiA8MHEp9'
                '6119euOIDh/TvMwctn08Ma5+sejz89U5njdi0P05Nyxn'
                '+5Jwu/Xd6VvuuvuWShZXvm/dU5JnYSHP1b+h8PsGuUMk'
                'l95Lrux/6Gzv0rObMPDAzILk+mp2d+1z49O9b/ne9Xnx'
                '9Qe+KP/EzzetL7e0+hXo3z19af+3HPUWvB+fP3H8vukn'
                'OyG/54y1f5cXWvt68Yvq8/Fu1qYfSP69trK78tOLn07n'
                'P6x/+b7j5dfG1/Gu7dqaeWOnFHnft94kPdRz23309J28'
                '/Of+sV93zNzYfu9yq5hydv3zu29jG6vaS15u+d/9fkfr'
                '1P9NGrROuAE1uKvg=')
        fd = StringIO.StringIO(zlib.decompress(base64.b64decode(data)))
        pipeline = cpp.Pipeline()
        pipeline.load(fd)
        self.assertEqual(len(pipeline.modules()),2)
        module = pipeline.modules()[1]
        self.assertTrue(isinstance(module,morph.Morph))
        self.assertEqual(module.image_name.value, "OrigBlue")
        self.assertEqual(module.output_image_name.value, "MorphBlue")
        self.assertEqual(len(module.functions),3)
        self.assertEqual(module.functions[0].function, morph.F_DILATE)
        self.assertEqual(module.functions[0].repeats_choice.value, morph.R_ONCE)
        self.assertEqual(module.functions[1].function, morph.F_ERODE)
        self.assertEqual(module.functions[1].repeats_choice.value, morph.R_CUSTOM)
        self.assertEqual(module.functions[1].custom_repeats.value, 2)
        self.assertEqual(module.functions[2].function, morph.F_FILL)
        self.assertEqual(module.functions[2].repeats_choice.value, morph.R_FOREVER)

    def test_01_02_load_v1(self):
        '''Load a revision 1 pipeline that has a morph module in it'''
        #
        # Pipeline has Morph as second module
        # input_name = OrigBlue
        # output_name = MorphBlue
        # dilate once
        # erode twice
        # fill forever
        #
        data = ('eJztWN1u2jAUdhDQskpre7Vd+nKa1ghYJ23ctLRsGlP50Yp6PZccqC'
                'UnjhwH0T3BHmOPssfp5R5hMU1IcClJI7qrBFnm2Oc7n89nJ47Ta48u'
                '2mf4g1nHvfboaEIZ4CEjcsKF3cKOfIfPBRAJFuZOC498wN98B9ebuN'
                'FoHTdbxw3crNc/oXyX0e29DKrfhwhVg3o3KKWwqxLaRqIo+xKkpM7U'
                'q6Ayeh22/wnKFRGUXDO4IswHL6aI2rvOhI9u3WVXj1s+gz6xk87B1f'
                'ftaxDeYBIBw+4hnQO7pD9BSyFy+w4z6lHuhPgwvt665OVS41U6fN2J'
                'dTA0HZQu+4n2hT+K/ctrdDtM+B+ENnUsOqOWTximNpkuR6HifUyJt6'
                'vFU/ZA0OlZILnCn6bgDzS8KiOYy6PPczKW2CZyfJMlTk2LU1voKtwb'
                'NZBEPvWUOMZKHAO9z6hDVeNXtkWDmwbu8Wnjf6Hhld3h2OES+x5kH3'
                '95JU4ZDZwxZMGVVnAl1Of59GqgbOvwlZavsjswIT6TuKsWIe5QAWPJ'
                'xW0m/StaPGWD4BZk1E3Pw0T55/3c9yS3s/FuS/dmxjzz8unrKtgUWB'
                '5cpz3sZtF1R9NV2V+4gBmIrTyXnkvfx/JN4qoaLroiXC2s8/D1ufMg'
                'v4Iv5rurPm0/zctzmpLXuuf9YvOdCu67z8+/bt+N+XHwSgDutua1wB'
                'W4AlfcxwXu/+PuEjh9v9PfB5X/D7R5vb1Fq+tN2WNgzBVcfScQpr04'
                'zHom48S6P02aF8HfbuJgqXiGKTxY48GP8djqkGcujnq6TrU1cZP5lo'
                'Lf/t5mfXVdY73/nuThKxkP+fZScOVQIYX7hZ42n282+Ee55fX/B9HP'
                '158=')
        fd = StringIO.StringIO(zlib.decompress(base64.b64decode(data)))
        pipeline = cpp.Pipeline()
        pipeline.load(fd)
        self.assertEqual(len(pipeline.modules()),2)
        module = pipeline.modules()[1]
        self.assertTrue(isinstance(module,morph.Morph))
        self.assertEqual(module.image_name.value, "OrigBlue")
        self.assertEqual(module.output_image_name.value, "MorphBlue")
        self.assertEqual(len(module.functions),3)
        self.assertEqual(module.functions[0].function, morph.F_DILATE)
        self.assertEqual(module.functions[0].repeats_choice.value, morph.R_ONCE)
        self.assertEqual(module.functions[1].function, morph.F_ERODE)
        self.assertEqual(module.functions[1].repeats_choice.value, morph.R_CUSTOM)
        self.assertEqual(module.functions[1].custom_repeats.value, 2)
        self.assertEqual(module.functions[2].function, morph.F_FILL)
        self.assertEqual(module.functions[2].repeats_choice.value, morph.R_FOREVER)

    def execute(self, image, function):
        '''Run the morph module on an input and return the resulting image'''
        INPUT_IMAGE_NAME = 'input'
        OUTPUT_IMAGE_NAME = 'output'
        module = morph.Morph()
        module.image_name.value = INPUT_IMAGE_NAME
        module.output_image_name.value = OUTPUT_IMAGE_NAME
        module.functions[0].function.value = function
        module.functions[0].repeats_choice.value = morph.R_ONCE
        pipeline = cpp.Pipeline()
        object_set = cpo.ObjectSet()
        image_set_list = cpi.ImageSetList()
        image_set = image_set_list.get_image_set(0)
        workspace = cpw.Workspace(pipeline,
                                  module,
                                  image_set,
                                  object_set,
                                  cpmeas.Measurements(),
                                  image_set_list)
        image_set.add(INPUT_IMAGE_NAME,cpi.Image(image))
        module.run(workspace)
        output = image_set.get_image(OUTPUT_IMAGE_NAME)
        return output.pixel_data
    
    def binary_tteesstt(self, function_name, function):
        np.random.seed(map(ord,function_name))
        input = np.random.uniform(size=(20,20)) > .7
        output = self.execute(input, function_name)
        expected = function(input) > 0
        self.assertTrue(np.all(output==expected))
        
    def test_02_01_binary_bothat(self):
        self.binary_tteesstt('bothat',cpmorph.black_tophat)
        
    def test_02_02_binary_bridge(self):
        self.binary_tteesstt('bridge', cpmorph.bridge)
    
    def test_02_03_binary_clean(self):
        self.binary_tteesstt('clean', cpmorph.clean)
    
    def test_02_04_binary_close(self):
        self.binary_tteesstt('close', lambda x:scind.binary_closing(x,np.ones((3,3),bool)))
    
    def test_02_05_binary_diag(self):
        self.binary_tteesstt('diag', cpmorph.diag)
    
    def test_02_06_binary_dilate(self):
        self.binary_tteesstt('dilate', lambda x: scind.binary_dilation(x, np.ones((3,3),bool)))
    
    def test_02_07_binary_erode(self):
        self.binary_tteesstt('erode', lambda x: scind.binary_erosion(x, np.ones((3,3),bool)))
    
    def test_02_08_binary_fill(self):
        self.binary_tteesstt('fill', cpmorph.fill)
    
    def test_02_09_binary_hbreak(self):
        self.binary_tteesstt('hbreak', cpmorph.hbreak)
    
    def test_02_10_binary_majority(self):
        self.binary_tteesstt('majority', cpmorph.majority)
    
    def test_02_11_binary_open(self):
        self.binary_tteesstt('open', lambda x: scind.binary_opening(x, np.ones((3,3),bool)))
    
    def test_02_12_binary_remove(self):
        self.binary_tteesstt('remove', cpmorph.remove)
    
    def test_02_13_binary_shrink(self):
        self.binary_tteesstt('shrink', lambda x:cpmorph.binary_shrink(x,1))
    
    def test_02_14_binary_skel(self):
        self.binary_tteesstt('skel', cpmorph.skeletonize)
    
    def test_02_15_binary_spur(self):
        self.binary_tteesstt('spur', cpmorph.spur)
    
    def test_02_16_binary_thicken(self):
        self.binary_tteesstt('thicken', cpmorph.thicken)
    
    def test_02_17_binary_thin(self):
        self.binary_tteesstt('thin', cpmorph.thin)
    
    def test_02_18_binary_tophat(self):
        self.binary_tteesstt('tophat', cpmorph.white_tophat)
    
    def test_02_19_binary_vbreak(self):
        self.binary_tteesstt('vbreak', cpmorph.vbreak)
    