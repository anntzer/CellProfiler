'''test_flagimages.py - Test the FlagImages module

CellProfiler is distributed under the GNU General Public License.
See the accompanying file LICENSE for details.

Developed by the Broad Institute
Copyright 2003-2009

Please see the AUTHORS file for credits.

Website: http://www.cellprofiler.org
'''

__version__="$Revision$"

import base64
import numpy as np
import os
import Image as PILImage
import scipy.ndimage
from StringIO import StringIO
import unittest
import zlib

import cellprofiler.pipeline as cpp
import cellprofiler.settings as cps
import cellprofiler.cpimage as cpi
import cellprofiler.workspace as cpw
import cellprofiler.objects as cpo
import cellprofiler.measurements as cpmeas

import cellprofiler.modules.flagimage as F

def image_measurement_name(index):
    return "Metadata_ImageMeasurement_%d"%index

OBJECT_NAME = "object"
def object_measurement_name(index):
    return "Measurement_Measurement_%d"%index

MEASUREMENT_CATEGORY = "MyCategory"
MEASUREMENT_FEATURE = "MyFeature"
MEASUREMENT_NAME = '_'.join((MEASUREMENT_CATEGORY,MEASUREMENT_FEATURE))

class TestFlagImages(unittest.TestCase):
    def test_01_01_load_matlab(self):
        data = ('eJzzdQzxcXRSMNUzUPB1DNFNy8xJ1VEIyEksScsvyrVSCHAO9/TTUXAuSk0s'
                'SU1RyM+zUnArylRwLE1XMDJUMDSwMjWzMrZQMDIwsFQgGTAwevryMzAwxDMx'
                'MFTMeTvdP/+ygciBuSZzrVpubRSe1fJEWXyBsNOjE9cCAzNfh1n5Pmq5J2W+'
                'ecqR0Ec5uup2bPNZCp8kF9xoPxg32cwwU3bTmpgNKa7nK99//3elzm82x8J4'
                '3ZZtRzYrLut8tljutFuWV6WHxfJ9wtcmts479tr+6J6GhkNLvfUO9Hp0iClH'
                'vv+ZXGY3WyduroF1kaf8ni2bJP6e2K3iWGHlx/P4enqJ1x3Fv04BZSpZ8idN'
                'eTU/J/+esX6d3h+jdT9yu37mVkeyO6909j1z98quK/Xt036F+d0tC/pl/dFG'
                'Pfjfo78ibjLVB9zDJ30OO5ypIaM5n+2KpcjSdYf2rd243eibmJWVxWvRk/XR'
                'H7WfNjcc+MCldvJ9RMvniIceO583OrMJ7phyXujcstcKxZpC/5WPrp/Sf5Pj'
                'jp60a+JHqyeFfRLfJI8HekyTiZVLa0te9Les8n9tm+2rYP1Pq84vzrExOHts'
                '8Wp33cMrF5q/LVtaWXOhYB7Q+vIj9x6xMH87ySu3+8GC9sehU5f3Tb7O78/B'
                'Lm1RY5dm7no+2PvhlktzHJdrb779pDLodxPPA7uy0KNr7Uo/qhSfM73wWnRO'
                'e9f6M/uW7fNdv1JXj8nn6VSBZwXdz9Z/O2q3elmfvvc1w/f/SphmtD56pWC5'
                'Z9HHlX/fTV5xa/+a6VL9/7mKLOPPfr2f/rLqbvn+e7lq6gkXl1SdW7W8b/51'
                '++k1On1MM9c8/v89fKJ98le7kO/FP987b6he2RbWcjnEImha+SnZ5aebHJdH'
                '+f2Kyc98lcCVuf2ixlX774GW9aWHfzyubzx3rqt0n/3uu7vvzv79t/Hfu+91'
                '+9zsJWdf+s9r7/LJDgCl2lmX')
        pipeline = cpp.Pipeline()
        def callback(caller,event):
            self.assertFalse(isinstance(event, cpp.LoadExceptionEvent))
        pipeline.add_listener(callback)
        pipeline.load(StringIO(zlib.decompress(base64.b64decode(data)))) 
        self.assertEqual(len(pipeline.modules()), 3)
        module = pipeline.modules()[1]
        self.assertTrue(isinstance(module, F.FlagImage))
        self.assertEqual(len(module.flags), 1)
        flag = module.flags[0]
        self.assertTrue(isinstance(flag, F.FlagSettings))
        self.assertEqual(len(flag.measurement_settings), 1)
        ms = flag.measurement_settings[0]
        self.assertTrue(isinstance(ms, F.MeasurementSettings))
        self.assertEqual(ms.measurement.value, "AreaShape_Area_OrigBlue")
        self.assertEqual(ms.source_choice, F.S_IMAGE)
        self.assertTrue(ms.wants_minimum.value)
        self.assertEqual(ms.minimum_value, 10)
        self.assertFalse(ms.wants_maximum.value)
        self.assertEqual(flag.category, "Metadata")
        self.assertEqual(flag.feature_name, "LowArea")

        module = pipeline.modules()[2]
        self.assertTrue(isinstance(module, F.FlagImage))
        self.assertEqual(len(module.flags), 1)
        flag = module.flags[0]
        self.assertTrue(isinstance(flag, F.FlagSettings))
        self.assertEqual(len(flag.measurement_settings), 1)
        ms = flag.measurement_settings[0]
        self.assertTrue(isinstance(ms, F.MeasurementSettings))
        self.assertEqual(ms.measurement.value, "ImageQuality_LocalFocus_OrigBlue")
        self.assertEqual(ms.source_choice, F.S_IMAGE)
        self.assertFalse(ms.wants_minimum.value)
        self.assertTrue(ms.wants_maximum.value)
        self.assertEqual(ms.maximum_value.value, 500)
        self.assertEqual(flag.category, "Metadata")
        self.assertEqual(flag.feature_name, "QCFlag")
    
    def test_01_02_load_v1(self):
        data = ('eJztW0Fv2zYUphInaFZgyC5r1124Q4FkqwXJXVAnGFJ59ooYqzOvCboVRdcx'
                'Nm1zoCRDorp4Q4H+rB33k3bccaIiWxIrW7IrK3YmAYT9KH7vfXx8fKREqFU7'
                'f1r7Fh7ICmzVzss9QjFsU8R6pqUfQYM9gHULI4a70DSO4BOLwJrThxUVquqR'
                'Wj16+AhWFOUQLHZJzdbH7o9SBWDb/b3llg3/1pYvS6HC5TPMGDH69hYogbt+'
                '/d9ueY4sgi4ofo6og+3AxLi+afTM89Fwcqtldh2KT5Eebuxep45+gS37h94Y'
                '6N9uk0tMz8gfWOjCuNkz/IbYxDR8vK9frJ3YNZlgl/vh33uBHyTBD5tuuR+q'
                '5+1PQNC+FOO3T0Ltd32ZGF3yhnQdRCHRUX/CwhuHBH2bEX2boHFaS4WTIjgJ'
                'VHx7WgJuV+DPyzm+ZOXvLlGHQR2xziCN/Y2Ing1waqbrr8j7YUo/LYorRXAl'
                'l6eBOa6agLsFon7icgsz1EUMpfHzRwKeyw0TGiaDju0HfBo9O4IeLtdHzBxS'
                'ZOsg0JPUn21BD5d/rD+hqJ/Oj4uO9zRcUr/j4pSzhaQHkTGCPURomvl6R9DD'
                '5QbuIYcy2OSTFTaIhTvMtEZLjactgQeXPfvgfT9uC/jxNcbv+L9Z4ebp57z5'
                '7IWbDT+EZzvB3j0Q9SuXmwbDhk3Y6HULXQYCT62p+58m3rP0d9bza1k8xfFV'
                'ZGUl43daHC6S9+sDZBiYVvKcb4p8eJDV/mEenlnmsTTruBqDW4U8lgaXZR6D'
                'IOpXLofyGDECYbL8c73vEvR+L+jl8i97j9vf8AcSfCx/tf+aSz9hSp+Zvx+/'
                'rJXbr/bHNXWTOrpx/FIpH776U31QeXvV+Iy4SK9yP3Yc8pjHgwRcVeg3lzn3'
                'FxhZfoe+frtf5lUt02ADv67i1zXQKKjJd94rBx+Yp9TrWKe0BFzafWxecaTG'
                'rFvzPGetan7NOm8tau9dAm7V81JSvv5c4M/lUL7GyHh/43mT8lbW+/z89qvq'
                'WvBcH38eriTPZe4zs8z3cet4+D1T3nxPEvh+KvDl8gnpDyZr+STtXY+/tQT+'
                'ad8rrVqc3MT3R3nw/DmB5xcg6lcuT1vHl7Vfzfs90irwXPf3SKvGUxx3uXqF'
                '2/0swEkCLu78a1l5N+48xDss61umM8zWPzcRp4HZ/r0Nov7lsnnxG+6wwMGr'
                'yLuIi/9nXBT9LXAFbv1xGpg9H+Oet4L8DonRxcN16m+RtwpcgZuO08DsOC/y'
                'wXrhNDB7PIu8VeAKXIErcAWuwE3HaSFcsY4WuAJ3vbiBFODEcxEuh899ePtf'
                'wez5+yWIzl8udzClQ8vk339Zsu59pGTL1ETdq6+E5Kfu32bogyFuZ5hgRxPs'
                'aNPs6BjZjoU9U2R8hCm3rmo9q5ODzTTnpHuC3b1pdnsU9T2jMj9W9wyJ47QT'
                'oz/s7w1XurN9f+b4iuMajPc/jxexV5Ikz174HP52Aq4U4sQvjv8LzBdXezPa'
                'j/uYV/v/ACB4EDk=')
        pipeline = cpp.Pipeline()
        def callback(caller,event):
            self.assertFalse(isinstance(event, cpp.LoadExceptionEvent))
        pipeline.add_listener(callback)
        pipeline.load(StringIO(zlib.decompress(base64.b64decode(data))))
        self.assertEqual(len(pipeline.modules()), 3)
        module = pipeline.modules()[2]
        self.assertTrue(isinstance(module, F.FlagImage))
        #
        # The module defines two flags:
        #
        # Metadata_QCFlag: flag if any fail
        #     Intensity_MaxIntensity_DNA: max = .95
        #     Intensity_MinIntensity_Cytoplasm: min = .05
        #     Intensity_MeanIntensity_DNA: min=.1, max=.9
        # Metadata_HighCytoplasmIntensity
        #     Intensity_MeanIntensity_Cytoplasm: max = .8
        #
        expected = (("QCFlag", F.C_ANY,
                     (("Intensity_MaxIntensity_DNA", None, .95),
                      ("Intensity_MinIntensity_Cytoplasm", .05, None),
                      ("Intensity_MeanIntensity_DNA", .1, .9))),
                    ("HighCytoplasmIntensity", None,
                     (("Intensity_MeanIntensity_Cytoplasm", None, .8),)))
        self.assertEqual(len(expected),module.flag_count.value)
        for flag, (feature_name, combine, measurements) \
            in zip(module.flags, expected):
            self.assertTrue(isinstance(flag, F.FlagSettings))
            self.assertEqual(flag.category, "Metadata")
            self.assertEqual(flag.feature_name, feature_name)
            if combine is not None:
                self.assertEqual(flag.combination_choice, combine)
            self.assertEqual(len(measurements), flag.measurement_count.value)
            for measurement, (measurement_name, min_value, max_value) \
                in zip(flag.measurement_settings,measurements):
                self.assertTrue(isinstance(measurement, F.MeasurementSettings))
                self.assertEqual(measurement.measurement, measurement_name)
                self.assertEqual(measurement.wants_minimum.value, min_value is not None)
                if measurement.wants_minimum.value:
                    self.assertAlmostEqual(measurement.minimum_value.value,
                                           min_value)
                self.assertEqual(measurement.wants_maximum.value, max_value is not None)
                if measurement.wants_maximum.value:
                    self.assertAlmostEqual(measurement.maximum_value.value,
                                           max_value)

    def make_workspace(self, image_measurements, object_measurements):
        '''Make a workspace with a FlagImage module and the given measurements
        
        image_measurements - a sequence of single image measurements. Use
                             image_measurement_name(i) to get the name of
                             the i th measurement
        object_measurements - a seequence of sequences of object measurements.
                              These are stored under object, OBJECT_NAME with
                              measurement name object_measurement_name(i) for
                              the i th measurement.
        
        returns module, workspace
        '''
        module = F.FlagImage()
        measurements = cpmeas.Measurements()
        for i in range(len(image_measurements)):
            measurements.add_image_measurement(image_measurement_name(i),
                                               image_measurements[i])
        for i in range(len(object_measurements)):
            measurements.add_measurement(OBJECT_NAME,
                                         object_measurement_name(i),
                                         np.array(object_measurements))
        flag = module.flags[0]
        self.assertTrue(isinstance(flag, F.FlagSettings))
        flag.category.value = MEASUREMENT_CATEGORY
        flag.feature_name.value = MEASUREMENT_FEATURE
        module.module_num = 1
        pipeline = cpp.Pipeline()
        def callback(caller,event):
            self.assertFalse(isinstance(event, cpp.RunExceptionEvent))
        pipeline.add_listener(callback)
        pipeline.add_module(module)
        image_set_list = cpi.ImageSetList()
        image_set = image_set_list.get_image_set(0)
        workspace = cpw.Workspace(pipeline, module, image_set, cpo.ObjectSet(),
                                  measurements, image_set_list)
        return module, workspace
    
    def test_02_01_positive_image_measurement(self):
        module, workspace = self.make_workspace([1],[])
        flag = module.flags[0]
        self.assertTrue(isinstance(flag, F.FlagSettings))
        measurement = flag.measurement_settings[0]
        self.assertTrue(isinstance(measurement, F.MeasurementSettings))
        measurement.measurement.value = image_measurement_name(0)
        measurement.wants_minimum.value = False
        measurement.wants_maximum.value = True
        measurement.maximum_value.value = .95
        module.run(workspace)
        m = workspace.measurements
        self.assertTrue(isinstance(m, cpmeas.Measurements))
        self.assertTrue(MEASUREMENT_NAME in m.get_feature_names(cpmeas.IMAGE))
        self.assertEqual(m.get_current_image_measurement(MEASUREMENT_NAME), 1)
    
    def test_02_02_negative_image_measurement(self):
        module, workspace = self.make_workspace([1],[])
        flag = module.flags[0]
        self.assertTrue(isinstance(flag, F.FlagSettings))
        measurement = flag.measurement_settings[0]
        self.assertTrue(isinstance(measurement, F.MeasurementSettings))
        measurement.measurement.value = image_measurement_name(0)
        measurement.wants_minimum.value = True
        measurement.minimum_value.value = .1
        measurement.wants_maximum.value = False
        module.run(workspace)
        m = workspace.measurements
        self.assertTrue(isinstance(m, cpmeas.Measurements))
        self.assertTrue(MEASUREMENT_NAME in m.get_feature_names(cpmeas.IMAGE))
        self.assertEqual(m.get_current_image_measurement(MEASUREMENT_NAME), 0)
        
    def test_03_01_positive_ave_object_measurement(self):
        for case in ("minimum", "maximum"):
            module, workspace = self.make_workspace([],[[.1,.2,.3,.4]])
            flag = module.flags[0]
            self.assertTrue(isinstance(flag, F.FlagSettings))
            measurement = flag.measurement_settings[0]
            self.assertTrue(isinstance(measurement, F.MeasurementSettings))
            measurement.source_choice.value = F.S_AVERAGE_OBJECT
            measurement.object_name.value = OBJECT_NAME
            measurement.measurement.value = object_measurement_name(0)
            if case == "minimum":
                measurement.wants_maximum.value = False
                measurement.wants_minimum.value = True
                measurement.minimum_value.value = .3
            else:
                measurement.wants_minimum.value = False
                measurement.wants_maximum.value = True
                measurement.maximum_value.value = .2
            module.run(workspace)
            m = workspace.measurements
            self.assertTrue(isinstance(m, cpmeas.Measurements))
            self.assertTrue(MEASUREMENT_NAME in m.get_feature_names(cpmeas.IMAGE))
            self.assertEqual(m.get_current_image_measurement(MEASUREMENT_NAME), 1)

    def test_03_02_negative_ave_object_measurement(self):
        for case in ("minimum", "maximum"):
            module, workspace = self.make_workspace([],[[.1,.2,.3,.4]])
            flag = module.flags[0]
            self.assertTrue(isinstance(flag, F.FlagSettings))
            measurement = flag.measurement_settings[0]
            self.assertTrue(isinstance(measurement, F.MeasurementSettings))
            measurement.source_choice.value = F.S_AVERAGE_OBJECT
            measurement.object_name.value = OBJECT_NAME
            measurement.measurement.value = object_measurement_name(0)
            if case == "minimum":
                measurement.wants_maximum.value = False
                measurement.wants_minimum.value = True
                measurement.minimum_value.value = .2
            else:
                measurement.wants_minimum.value = False
                measurement.wants_maximum.value = True
                measurement.maximum_value.value = .3
            module.run(workspace)
            m = workspace.measurements
            self.assertTrue(isinstance(m, cpmeas.Measurements))
            self.assertTrue(MEASUREMENT_NAME in m.get_feature_names(cpmeas.IMAGE))
            self.assertEqual(m.get_current_image_measurement(MEASUREMENT_NAME), 0)

    def test_04_01_positive_object_measurement(self):
        for case in ("minimum","maximum"):
            module, workspace = self.make_workspace([],[[.1,.2,.3,.4]])
            flag = module.flags[0]
            self.assertTrue(isinstance(flag, F.FlagSettings))
            measurement = flag.measurement_settings[0]
            self.assertTrue(isinstance(measurement, F.MeasurementSettings))
            measurement.source_choice.value = F.S_ALL_OBJECTS
            measurement.object_name.value = OBJECT_NAME
            measurement.measurement.value = object_measurement_name(0)
            if case == "maximum":
                measurement.wants_minimum.value = False
                measurement.wants_maximum.value = True
                measurement.maximum_value.value = .35
            else:
                measurement.wants_maximum.value = False
                measurement.wants_minimum.value = True
                measurement.minimum_value.value = .15
            module.run(workspace)
            m = workspace.measurements
            self.assertTrue(isinstance(m, cpmeas.Measurements))
            self.assertTrue(MEASUREMENT_NAME in m.get_feature_names(cpmeas.IMAGE))
            self.assertEqual(m.get_current_image_measurement(MEASUREMENT_NAME), 1)

    def test_04_02_negative_object_measurement(self):
        for case in ("minimum","maximum"):
            module, workspace = self.make_workspace([],[[.1,.2,.3,.4]])
            flag = module.flags[0]
            self.assertTrue(isinstance(flag, F.FlagSettings))
            measurement = flag.measurement_settings[0]
            self.assertTrue(isinstance(measurement, F.MeasurementSettings))
            measurement.source_choice.value = F.S_ALL_OBJECTS
            measurement.object_name.value = OBJECT_NAME
            measurement.measurement.value = object_measurement_name(0)
            if case == "maximum":
                measurement.wants_minimum.value = False
                measurement.wants_maximum.value = True
                measurement.maximum_value.value = .45
            else:
                measurement.wants_maximum.value = False
                measurement.wants_minimum.value = True
                measurement.minimum_value.value = .05
            module.run(workspace)
            m = workspace.measurements
            self.assertTrue(isinstance(m, cpmeas.Measurements))
            self.assertTrue(MEASUREMENT_NAME in m.get_feature_names(cpmeas.IMAGE))
            self.assertEqual(m.get_current_image_measurement(MEASUREMENT_NAME), 0)
    
    def test_05_01_two_measurements_any(self):
        for measurements, expected in (((0,0),0),
                                       ((0,1),1),
                                       ((1,0),1),
                                       ((1,1),1)):
            module, workspace = self.make_workspace(measurements,[])
            flag = module.flags[0]
            self.assertTrue(isinstance(flag, F.FlagSettings))
            flag.combination_choice.value = F.C_ANY
            flag.add_measurement()
            for i in range(2):
                measurement = flag.measurement_settings[i]
                self.assertTrue(isinstance(measurement, F.MeasurementSettings))
                measurement.measurement.value = image_measurement_name(i)
                measurement.wants_minimum.value = False
                measurement.wants_maximum.value = True
                measurement.maximum_value.value = .5
            module.run(workspace)
            m = workspace.measurements
            self.assertTrue(isinstance(m, cpmeas.Measurements))
            self.assertTrue(MEASUREMENT_NAME in m.get_feature_names(cpmeas.IMAGE))
            self.assertEqual(m.get_current_image_measurement(MEASUREMENT_NAME),
                             expected)
        
    def test_05_02_two_measurements_all(self):
        for measurements, expected in (((0,0),0),
                                       ((0,1),0),
                                       ((1,0),0),
                                       ((1,1),1)):
            module, workspace = self.make_workspace(measurements,[])
            flag = module.flags[0]
            self.assertTrue(isinstance(flag, F.FlagSettings))
            flag.combination_choice.value = F.C_ALL
            flag.add_measurement()
            for i in range(2):
                measurement = flag.measurement_settings[i]
                self.assertTrue(isinstance(measurement, F.MeasurementSettings))
                measurement.measurement.value = image_measurement_name(i)
                measurement.wants_minimum.value = False
                measurement.wants_maximum.value = True
                measurement.maximum_value.value = .5
            module.run(workspace)
            m = workspace.measurements
            self.assertTrue(isinstance(m, cpmeas.Measurements))
            self.assertTrue(MEASUREMENT_NAME in m.get_feature_names(cpmeas.IMAGE))
            self.assertEqual(m.get_current_image_measurement(MEASUREMENT_NAME),
                             expected)
    
    def test_06_01_get_measurement_columns(self):
        module = F.FlagImage()
        module.add_flag()
        module.flags[0].category.value = 'Foo'
        module.flags[0].feature_name.value = 'Bar'
        module.flags[1].category.value = 'Hello'
        module.flags[1].feature_name.value = 'World'
        columns = module.get_measurement_columns(None)
        self.assertEqual(len(columns),2)
        self.assertTrue(all([column[0] == cpmeas.IMAGE and
                             column[1] in ("Foo_Bar","Hello_World") and
                             column[2] == cpmeas.COLTYPE_INTEGER
                             for column in columns]))
        self.assertNotEqual(columns[0][1], columns[1][1])
        categories = module.get_categories(None, 'foo')
        self.assertEqual(len(categories), 0)
        categories = module.get_categories(None, cpmeas.IMAGE)
        self.assertEqual(len(categories), 2)
        self.assertTrue('Foo' in categories)
        self.assertTrue('Hello' in categories)
        self.assertEqual(len(module.get_measurements(None, cpmeas.IMAGE, 'Whatever')), 0)
        for category, feature in (('Foo','Bar'), ('Hello','World')):
            features = module.get_measurements(None, cpmeas.IMAGE, category)
            self.assertEqual(len(features), 1)
            self.assertEqual(features[0], feature)
                             