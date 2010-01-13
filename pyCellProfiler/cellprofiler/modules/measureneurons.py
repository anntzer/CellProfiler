'''<b>Measure Neurons</b>: This module will measure branching information of
skeleton objects from seed points.
<hr>
This module measures the number of trunks and branches for each neuron in
an image. The module takes a skeletonized image of the neuron and seed objects
(for instance, the neuron soma) and finds the number of axon or dendrite
trunks that emerge from the soma and the number of branches along the
axons and dendrites.

The module finds distances from the seed objects along the axons and dendrites 
and assigns branchpoints to the closest seed object when two seed objects
appear to be attached to the same dendrite or axon.
'''
# CellProfiler is distributed under the GNU General Public License.
# See the accompanying file LICENSE for details.
#
# Developed by the Whitehead Institute for Biomedical Research.
# Copyright 2003-2010
#
# Please see the AUTHORS file for credits.
#
# Website: http://www.cellprofiler.org
#
__version__="$Revision$"

import numpy as np
from scipy.ndimage import binary_erosion
import scipy.ndimage as scind

import cellprofiler.cpimage as cpi
import cellprofiler.cpmodule as cpm
import cellprofiler.measurements as cpmeas
import cellprofiler.settings as cps
import cellprofiler.cpmath.cpmorphology as morph
from cellprofiler.cpmath.cpmorphology import fixup_scipy_ndimage_result as fix
import cellprofiler.cpmath.propagate as propagate

'''The measurement category'''
C_NEURON = "Neuron"

'''The trunk count feature'''
F_NUMBER_TRUNKS = "NumberTrunks"

'''The branch feature'''
F_NUMBER_NON_TRUNK_BRANCHES = "NumberNonTrunkBranches"

class MeasureNeurons(cpm.CPModule):
    
    module_name = "MeasureNeurons"
    category = "Measurement"
    variable_revision_number = 1
    
    def create_settings(self):
        '''Create the UI settings for the module'''
        self.seed_objects_name = cps.ObjectNameSubscriber(
            "Seed objects name:", "None",
            doc = """This setting selects the objects that are used as the
            seeds for distance measurement. Branches and trunks are assigned
            per seed object""")
        self.image_name = cps.ImageNameSubscriber(
            "Skeletonized image name:", "None",
            doc = """This should be a skeletonized image of the dendrites
            and / or axons as produced by the <b>Morph</b> module's
            "skeletonize" operation""")
        self.wants_branchpoint_image = cps.Binary(
            "Do you want to save the branchpoint image?", False,
            doc="""Check this setting if you want to save the color image of
            branchpoints and trunks. This is the image that is displayed
            as the visualization for this module.""")
        self.branchpoint_image_name = cps.ImageNameProvider(
            "Branchpoint image name:","BranchpointImage",
            doc="""Enter a name for the branchpoint image here. You can
            use this name in a later module, such as <b>SaveImages</b> to
            refer to this image.""")
    
    def settings(self):
        '''The settings, in the order that they are saved in the pipeline'''
        return [self.seed_objects_name, self.image_name,
                self.wants_branchpoint_image, self.branchpoint_image_name]
    
    def visible_settings(self):
        '''The settings that are displayed in the GUI'''
        result = [self.seed_objects_name, self.image_name,
                  self.wants_branchpoint_image]
        if self.wants_branchpoint_image:
            result += [self.branchpoint_image_name]
        return result
    
    def is_interactive(self):
        '''Indicates that this module has separate "run" and "display" functions'''
        return False
    
    def run(self, workspace):
        '''Run the module on the image set'''
        seed_objects_name = self.seed_objects_name.value
        skeleton_name = self.image_name.value
        seed_objects = workspace.object_set.get_objects(seed_objects_name)
        labels = seed_objects.segmented
        labels_count = np.max(labels)
        label_range = np.arange(labels_count)+1
        
        skeleton_image = workspace.image_set.get_image(
            skeleton_name, must_be_binary = True)
        skeleton = skeleton_image.pixel_data
        if skeleton_image.has_mask:
            skeleton = skeleton & skeleton_image.mask
        labels = skeleton_image.crop_image_similarly(labels)
        #
        # The following code makes a ring around the seed objects with
        # the skeleton trunks sticking out of it.
        #
        # Create a new skeleton with holes at the seed objects
        # First combine the seed objects with the skeleton so
        # that the skeleton trunks come out of the seed objects.
        #
        # Erode the labels once so that all of the trunk branchpoints
        # will be within the labels
        #
        seed_mask = binary_erosion((labels > 0))
        combined_skel = skeleton | seed_mask
        #
        # Shrink the objects, then subtract them to make a ring
        #
        my_disk = morph.strel_disk(1.5)
        seed_center = binary_erosion(seed_mask, my_disk)
        combined_skel = combined_skel & (~seed_center)
        #
        # Fill in single holes
        #
        combined_skel = morph.fill4(combined_skel)
        #
        # Reskeletonize to make true branchpoints at the ring boundaries
        #
        combined_skel = morph.skeletonize(combined_skel)
        #
        # Associate all skeleton points with seed objects
        #
        dlabels, distance_map = propagate.propagate(np.zeros(labels.shape),
                                                    labels,
                                                    combined_skel, 1)
        #
        # Find the branchpoints
        #
        branch_points = morph.branchpoints(combined_skel)
        #
        # The trunks are the branchpoints that lie within the seed objects.
        #
        if labels_count > 0:
            trunk_counts = fix(scind.sum(branch_points, labels, label_range))
        else:
            trunk_counts = np.zeros((0,),int)
        #
        # The branches are the branchpoints that lie outside the seed objects
        #
        outside_labels = dlabels.copy()
        outside_labels[labels > 0] = 0
        if labels_count > 0:
            branch_counts = fix(scind.sum(branch_points, outside_labels, 
                                          label_range))
        else:
            branch_counts = np.zeros((0,),int)
        #
        # Save measurements
        #
        m = workspace.measurements
        assert isinstance(m, cpmeas.Measurements)
        feature = "_".join((C_NEURON, F_NUMBER_TRUNKS, skeleton_name))
        m.add_measurement(seed_objects_name, feature, trunk_counts)
        feature = "_".join((C_NEURON, F_NUMBER_NON_TRUNK_BRANCHES, 
                            skeleton_name))
        m.add_measurement(seed_objects_name, feature, branch_counts)
        #
        # Make the display image
        #
        if workspace.frame is not None or self.wants_branchpoint_image:
            branchpoint_image = np.zeros((skeleton.shape[0],
                                          skeleton.shape[1],
                                          3))
            trunk_mask = branch_points & (labels != 0)
            branch_mask = branch_points & (labels == 0)
            branchpoint_image[skeleton,2] = 1
            branchpoint_image[trunk_mask,0] = 1
            branchpoint_image[branch_mask,1] = 1
            branchpoint_image[trunk_mask | branch_mask,2] = 0
            branchpoint_image[labels != 0,:] *= .875
            branchpoint_image[labels != 0,:] += .1
            if workspace.frame:
                workspace.display_data.branchpoint_image = branchpoint_image
            if self.wants_branchpoint_image:
                bi = cpi.Image(branchpoint_image,
                               parent_image = skeleton_image)
                workspace.image_set.add(self.branchpoint_image_name.value, bi)
    
    def display(self, workspace):
        '''Display a visualization of the results'''
        figure = workspace.create_or_find_figure(subplots=(1,1))
        title = ("Branchpoints of %s and %s\nTrunks are red, others are green" %
                 (self.seed_objects_name.value, self.image_name.value))
        figure.subplot_imshow_color(0, 0,
                                    workspace.display_data.branchpoint_image,
                                    title)
    def get_measurement_columns(self, pipeline):
        '''Return database column definitions for measurements made here'''
        return [(self.seed_objects_name.value,
                 "_".join((C_NEURON, feature, self.image_name.value)),
                 cpmeas.COLTYPE_INTEGER)
                for feature in (F_NUMBER_TRUNKS, F_NUMBER_NON_TRUNK_BRANCHES)]
    
    def get_categories(self, pipeline, object_name):
        '''Get the measurement categories generated by this module
        
        pipeline - pipeline being run
        object_name - name of seed object
        '''
        if object_name == self.seed_objects_name:
            return [ C_NEURON ]
        else:
            return []
        
    def get_measurements(self, pipeline, object_name, category):
        '''Return the measurement features generated by this module
        
        pipeline - pipeline being run
        object_name - object being measured (must be the seed object)
        category - category of measurement (must be C_NEURON)
        '''
        if category == C_NEURON and object_name == self.seed_objects_name:
            return [ F_NUMBER_TRUNKS, F_NUMBER_NON_TRUNK_BRANCHES ]
        else:
            return []
        
    def get_measurement_images(self, pipeline, object_name, category, 
                               measurement):
        '''Return the images measured by this module
        
        pipeline - pipeline being run
        object_name - object being measured (must be the seed object)
        category - category of measurement (must be C_NEURON)
        measurement - one of the neuron measurements
        '''
        if measurement in self.get_measurements(pipeline, object_name, 
                                                category):
            return [ self.image_name.value]
        else:
            return []
    
    def upgrade_settings(self, setting_values, variable_revision_number,
                         module_name, from_matlab):
        '''Provide backwards compatibility for old pipelines
        
        setting_values - the strings to be fed to settings
        variable_revision_number - the version number at time of saving
        module_name - name of original module
        from_matlab - true if a matlab pipeline, false if pyCP
        '''
        if from_matlab and variable_revision_number == 1:
            #
            # Added "Wants branchpoint image" and branchpoint image name 
            #
            setting_values = setting_values + [cps.NO, "Branchpoints"]
            from_matlab = False
            variable_revision_number = 1
        return setting_values, variable_revision_number, from_matlab