"""
CellProfiler is distributed under the GNU General Public License.
See the accompanying file LICENSE for details.

Copyright (c) 2003-2009 Massachusetts Institute of Technology
Copyright (c) 2009-2013 Broad Institute
All rights reserved.

Please see the AUTHORS file for credits.

Website: http://www.cellprofiler.org
"""

import h5py
import logging
import logging.config
import sys
import os
import numpy as np
import tempfile
from cStringIO import StringIO

if sys.platform.startswith('win'):
    # This recipe is largely from zmq which seems to need this magic
    # in order to import in frozen mode - a topic the developers never
    # dealt with.
    if hasattr(sys, 'frozen'):
        here = os.path.split(sys.argv[0])[0]

        import ctypes
        libzmq = os.path.join(here, 'libzmq.dll')
        if os.path.exists(libzmq):
            ctypes.cdll.LoadLibrary(libzmq)
import zmq
#
# CellProfiler expects NaN as a result during calculation
#
np.seterr(all='ignore')

if not hasattr(sys, 'frozen'):
    root = os.path.split(__file__)[0]
else:
    root = os.path.split(sys.argv[0])[0]
if len(root) == 0:
    root = os.curdir
root = os.path.abspath(root)
site_packages = os.path.join(root, 'site-packages').encode('utf-8')
if os.path.exists(site_packages) and os.path.isdir(site_packages):
    import site
    site.addsitedir(site_packages)
    
def main(args):
    '''Run CellProfiler

    args - command-line arguments, e.g. sys.argv
    '''
    if any([arg.startswith('--work-announce') for arg in args]):
        #
        # Go headless ASAP
        #
        import cellprofiler.preferences as cpprefs
        cpprefs.set_headless()
        import cellprofiler.analysis_worker
        cellprofiler.analysis_worker.aw_parse_args()
        cellprofiler.analysis_worker.main()
        sys.exit(0)
        
    options, args = parse_args(args)
    set_log_level(options)
    
    if not hasattr(sys, "frozen") and options.code_statistics:
        print_code_statistics()
        return
    
    if options.print_groups_file is not None:
        print_groups(options.print_groups_file)
        return
    
    if options.batch_commands_file is not None:
        get_batch_commands(options.batch_commands_file)
        return
        
    if options.run_ilastik:
        run_ilastik()
        return
    
    if options.add_message_for_user:
        if len(args) != 3:
            sys.stderr.write("Usage: (for add_message-for-user)\n")
            sys.stderr.write("CellProfiler --add-message-for-user <caption> <message> <pipeline-or-project>\n")
            sys.stderr.write("where:\n")
            sys.stderr.write("    <caption> - the message box caption\n")
            sys.stderr.write("    <message> - the message displayed inside the message box\n")
            sys.stderr.write("    <pipeline-or-project> - the path to the pipeline or project file to modify\n")
            return
        caption = args[0]
        message = args[1]
        path = args[2]
        
        import h5py
        using_hdf5 = h5py.is_hdf5(path)
        if using_hdf5:
            import cellprofiler.measurements as cpmeas
            m = cpmeas.Measurements(
                filename = path, mode="r+")
            pipeline_text = m[cpmeas.EXPERIMENT, "Pipeline_Pipeline"]
        else:
            with open(path, "r") as fd:
                pipeline_text = fd.read()
        header, body = pipeline_text.split("\n\n", 1)
        pipeline_text = header + \
            ("\nMessageForUser:%s|%s\n\n" % (caption, message)) + body
        if using_hdf5:
            m[cpmeas.EXPERIMENT, "Pipeline_Pipeline"] = pipeline_text
            m.close()
        else:
            with open(path, "w") as fd:
                fd.write(pipeline_text)
        print "Message added to %s" % path
        return
    
    # necessary to prevent matplotlib trying to use Tkinter as its backend.
    # has to be done before CellProfilerApp is imported
    from matplotlib import use as mpluse
    mpluse('WXAgg')
    
    if (not hasattr(sys, 'frozen')) and options.fetch_external_dependencies:
        import external_dependencies
        external_dependencies.fetch_external_dependencies(options.overwrite_external_dependencies)
    
    if (not hasattr(sys, 'frozen')) and options.build_extensions:
        build_extensions()
        if options.build_and_exit:
            return
    
    if options.output_html:
        from cellprofiler.gui.html.manual import generate_html
        webpage_path = options.output_directory if options.output_directory else None
        generate_html(webpage_path)
        return
    if options.print_measurements:
        print_measurements(options)
        return
    
    try:
        if options.show_gui:
            import wx
            wx.Log.EnableLogging(False)
            from cellprofiler.cellprofilerapp import CellProfilerApp
            show_splashbox = (options.pipeline_filename is None and
                              options.project_filename is None and
                              (not options.new_project) and
                              options.show_splashbox)
            if options.project_filename:
                workspace_path = os.path.expanduser(options.project_filename)
            elif options.new_project:
                workspace_path = False
            else:
                workspace_path = None
            App = CellProfilerApp(
                0, 
                check_for_new_version = (options.pipeline_filename is None),
                show_splashbox = show_splashbox,
                workspace_path = workspace_path)
    
        #
        # Important to go headless ASAP
        #
        # cellprofiler.preferences can't be imported before we have a chance
        # to initialize the wx app.
        #
        import cellprofiler.preferences as cpprefs
        if not options.show_gui:
            cpprefs.set_headless()
            # What's there to do but run if you're running headless?
            # Might want to change later if there's some headless setup 
            options.run_pipeline = True
    
            
        if options.plugins_directory is not None:
            cpprefs.set_plugin_directory(options.plugins_directory)
        if options.ij_plugins_directory is not None:
            cpprefs.set_ij_plugin_directory(options.ij_plugins_directory)
        if options.temp_dir is not None:
            cpprefs.set_temporary_directory(options.temp_dir)
        if options.data_file is not None:
            cpprefs.set_data_file(os.path.abspath(options.data_file))
        if options.image_set_file is not None:
            cpprefs.set_image_set_file(options.image_set_file, False)
            
        from cellprofiler.utilities.version import version_string, version_number
        logging.root.info("Version: %s / %d" % (version_string, version_number))
    
        if options.run_pipeline and not options.pipeline_filename:
            raise ValueError("You must specify a pipeline filename to run")
    
        if options.output_directory:
            cpprefs.set_default_output_directory(options.output_directory)
        
        if options.image_directory:
            cpprefs.set_default_image_directory(options.image_directory)
    
        if options.show_gui:
            import cellprofiler.gui.cpframe as cpgframe
            if options.pipeline_filename:
                pipeline_path = os.path.expanduser(options.pipeline_filename)
                try:
                    App.frame.pipeline.load(pipeline_path)
                    if options.run_pipeline:
                        App.frame.Command(cpgframe.ID_FILE_ANALYZE_IMAGES)
                except:
                    import wx
                    wx.MessageBox(
                        'CellProfiler was unable to load the pipeline file, "%s"' %
                        options.pipeline_filename, "Error loading pipeline",
                        style = wx.OK | wx.ICON_ERROR)
                    logging.root.error("Unable to load pipeline", exc_info=True)
            App.MainLoop()
            return
        
        elif options.run_pipeline:
            run_pipeline_headless(options, args)
    except Exception, e:
        logging.root.fatal("Uncaught exception in CellProfiler.py", exc_info=True)
        raise
    
    finally:
        if __name__ == "__main__":
            try:
                from ilastik.core.jobMachine import GLOBAL_WM
                GLOBAL_WM.stopWorkers()
            except:
                logging.root.warn("Failed to stop Ilastik")
            try:
                from cellprofiler.utilities.zmqrequest import join_to_the_boundary
                join_to_the_boundary()
            except:
                logging.root.warn("Failed to stop zmq boundary")
            try:
                from cellprofiler.utilities.jutil import kill_vm
                kill_vm()
            except:
                logging.root.warn("Failed to stop the JVM")
            os._exit(0)

def parse_args(args):
    '''Parse the CellProfiler command-line arguments'''
    import optparse
    usage = """usage: %prog [options] [<output-file>])
         where <output-file> is the optional filename for the output file of measurements
               when running headless"""
    
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-p", "--pipeline",
                      dest="pipeline_filename",
                      help="Load this pipeline file on startup",
                      default=None)
    parser.add_option("-w", "--project",
                      dest="project_filename",
                      help="Load this project on startup",
                      default=None)
    parser.add_option("-n", "--new-project",
                      dest="new_project",
                      help="Open a new project, prompting for its name using a file dialog",
                      action="store_true",
                      default=False)
    parser.add_option("-c", "--run-headless",
                      action="store_false",
                      dest="show_gui",
                      default=True,
                      help="Run headless (without the GUI)")
    parser.add_option("-r", "--run",
                      action="store_true",
                      dest="run_pipeline",
                      default=False,
                      help="Run the given pipeline on startup")
    
    
    parser.add_option("-o", "--output-directory",
                      dest="output_directory",
                      default=None,
                      help="Make this directory the default output folder")
    parser.add_option("-i", "--image-directory",
                      dest="image_directory",
                      default=None,
                      help="Make this directory the default input folder")
    parser.add_option("-f", "--first-image-set",
                      dest="first_image_set",
                      default=None,
                      help="The one-based index of the first image set to process")
    parser.add_option("-l", "--last-image-set",
                      dest="last_image_set",
                      default=None,
                      help="The one-based index of the last image set to process")
    parser.add_option("-g", "--group",
                      dest="groups",
                      default=None,
                      help=('Restrict processing to one grouping in a grouped '
                            'pipeline. For instance, "-g ROW=H,COL=01", will '
                            'process only the group of image sets that match '
                            'the keys.'))
    parser.add_option("--html",
                      action="store_true",
                      dest="output_html",
                      default = False,
                      help = ('Output HTML help for all modules. Use with the -o '
                              'option to specify the output directory for the '
                              'files. Assumes -b.'))
    
    parser.add_option("--plugins-directory",
                      dest="plugins_directory",
                      help=("CellProfiler will look for plugin modules in this "
                            "directory (headless-only)."))
    
    parser.add_option("--ij-plugins-directory",
                      dest="ij_plugins_directory",
                      help=("CellProfiler will look for ImageJ plugin modules "
                            "in this directory (headless-only)."))
    
    parser.add_option("-t", "--temporary-directory",
                      dest="temp_dir",
                      default = None,
                      help=("The temporary directory if in headless mode. "
                            "CellProfiler uses this for downloaded image files "
                            "and for the measurements file, if not specified. "
                            "The default is " + tempfile.gettempdir()))
    
    parser.add_option("--jvm-heap-size",
                      dest="jvm_heap_size",
                      default="512m",
                      help=("This is the amount of memory reserved for the "
                            "Java Virtual Machine (similar to the java -Xmx switch)."
                            "Example formats: 512000k, 512m, 1g"))
    
    parser.add_option("--add-message-for-user",
                      dest="add_message_for_user",
                      default=False,
                      action="store_true",
                      help = ("This option lets you add a message to a pipeline "
                              "or project file which will appear in a message box"
                              "when that pipeline or project file is opened. "))
    
    if not hasattr(sys, 'frozen'):
        parser.add_option("-b", "--do-not-build", "--do-not_build",
                          dest="build_extensions",
                          default=True,
                          action="store_false",
                          help="Do not build C and Cython extensions")
        parser.add_option("--build-and-exit",
                          dest="build_and_exit",
                          default=False,
                          action="store_true",
                          help="Build extensions, then exit CellProfiler")
        parser.add_option("--do-not-fetch",
                          dest="fetch_external_dependencies",
                          default=True,
                          action="store_false",
                          help="Do not fetch external binary dependencies")
        parser.add_option("--fetch-and-overwrite",
                          dest="overwrite_external_dependencies",
                          default=False,
                          action="store_true",
                          help="Overwrite external binary depencies if hash does not match")
    
    parser.add_option("--no-splash-screen",
                      dest="show_splashbox",
                      action="store_false",
                      default=True,
                      help="Do not show the splash screen when starting CellProfiler")
    parser.add_option("--ilastik",
                      dest = "run_ilastik",
                      default=False,
                      action="store_true",
                      help = ("Run Ilastik instead of CellProfiler. "
                              "Ilastik is a pixel-based classifier. See "
                              "www.ilastik.org for more details."))
    parser.add_option("-d", "--done-file",
                      dest="done_file",
                      default=None,
                      help=('The path to the "Done" file, written by CellProfiler'
                            ' shortly before exiting'))
    parser.add_option("--measurements",
                      dest="print_measurements",
                      default=False,
                      action="store_true",
                      help="Open the pipeline file specified by the -p switch "
                      "and print the measurements made by that pipeline")
    
    parser.add_option("--print-groups",
                      dest="print_groups_file",
                      default=None,
                      help = "Open the measurements file following the "
                      "--print-groups switch and print the groups in its image "
                      "sets. The measurements file should be generated using "
                      "CreateBatchFiles. The output is a JSON-encoded data "
                      "structure containing the group keys and values and the "
                      "image sets in each group.")
    parser.add_option("--get-batch-commands",
                      dest = "batch_commands_file",
                      default = None,
                      help = "Open the measurements file following the "
                      "--get-batch-commands switch and print one line to the "
                      "console per group. The measurements file should be "
                      "generated using CreateBatchFiles and the image sets "
                      "should be grouped into the units to be run. Each line "
                      "is a command to invoke CellProfiler. You can use this "
                      "option to generate a shell script that will invoke "
                      'CellProfiler on a cluster by substituting "CellProfiler" '
                      "with your invocation command in the script's text, for "
                      "instance: CellProfiler --get-batch-commands Batch_data.h5 | sed s/CellProfiler/farm_jobs.sh")
    
    parser.add_option("--data-file",
                      dest="data_file",
                      default = None,
                      help = "Specify a data file for LoadData modules that "
                      'use the "From command-line" option')
    parser.add_option("--image-set-file",
                      dest = "image_set_file",
                      default = None,
                      help = "Specify the image set file that controls the input "
                      "images for the pipeline")
                      
    parser.add_option("-L", "--log-level",
                      dest = "log_level",
                      default = str(logging.INFO),
                      help = ("Set the verbosity for logging messages: " +
                              ("%d or %s for debugging, " % (logging.DEBUG, "DEBUG")) +
                              ("%d or %s for informational, " % (logging.INFO, "INFO")) +
                              ("%d or %s for warning, " % (logging.WARNING, "WARNING")) +
                              ("%d or %s for error, " % (logging.ERROR, "ERROR")) +
                              ("%d or %s for critical, " % (logging.CRITICAL, "CRITICAL")) +
                              ("%d or %s for fatal." % (logging.FATAL, "FATAL")) +
                              " Otherwise, the argument is interpreted as the file name of a log configuration file (see http://docs.python.org/library/logging.config.html for file format)"))
    
    if not hasattr(sys, 'frozen'):
        parser.add_option("--code-statistics", 
                          dest = "code_statistics",
                          action = "store_true",
                          default = False,
                          help = "Print the number of modules, settings and lines of code")
                                  
    options, result_args = parser.parse_args(args[1:])
    if sys.platform == 'darwin' and len(args) == 2:
        if args[1].lower().endswith(".cpproj"):
            # Assume fakey open of .cpproj and OS can't be configured to
            # add the switch as it can in Windows.
            options.project_filename = args[1]
            result_args = []
        elif args[1].lower().endswith(".cpproj"):
            options.pipeline_filename = args[1]
            result_args = []
    return options, result_args

def set_log_level(options):
    '''Set the logging package's log level based on command-line options'''
    try:
        if options.log_level.isdigit():
            logging.root.setLevel(int(options.log_level))
        else:
            logging.root.setLevel(options.log_level)
        if len(logging.root.handlers) == 0:
            logging.root.addHandler(logging.StreamHandler())
    except ValueError:
        logging.config.fileConfig(options.log_level)

def print_code_statistics():
    '''Print # lines of code, # modules, etc to console
    
    This is the official source of code statistics for things like grants.
    '''
    from cellprofiler.modules import builtin_modules, all_modules, instantiate_module
    import subprocess
    print "\n\n\n**** CellProfiler code statistics ****"
    print "# of built-in modules: %d" % len(builtin_modules)
    setting_count = 0
    for module in all_modules.values():
        if module.__module__.find(".") < 0:
            continue
        mn = module.__module__.rsplit(".", 1)[1]
        if mn not in builtin_modules:
            continue
        module_instance = instantiate_module(module.module_name)
        setting_count += len(module_instance.help_settings())
    directory = os.path.abspath(os.path.split(sys.argv[0])[0])
    try:
        filelist = subprocess.Popen(
            ["git", "ls-files"], 
            stdout=subprocess.PIPE,
            cwd = directory).communicate()[0].split("\n")
    except:
        filelist = []
        for root, dirs, files in os.walk(directory):
            filelist += [os.path.join(root, f) for f in files]
    linecount = 0
    for filename in filelist:
        if (os.path.exists(filename) and 
            any([filename.endswith(x) for x in ".py", ".c", ".pyx", ".java"])):
            if filename.endswith(".c") and os.path.exists(filename[:-1]+"pyx"):
                continue
            with open(filename, "r") as fd:
                linecount += len(fd.readlines())
    print "# of settings: %d" % setting_count
    print "# of lines of code: %d" % linecount

def print_measurements(options):
    '''Print the measurements that would be output by a pipeline
    
    This function calls Pipeline.get_measurement_columns() to get the
    measurements that would be output by a pipeline. This can be used in
    a workflow tool or LIMS to find the outputs of a pipeline without
    running it. For instance, someone might want to integrate CellProfiler
    with Knime and write a Knime node that let the user specify a pipeline
    file. The node could then execute CellProfiler with the --measurements
    switch and display the measurements as node outputs.
    '''
    
    if options.pipeline_filename is None:
        raise ValueError("Can't print measurements, no pipeline file")
    import cellprofiler.pipeline as cpp
    pipeline = cpp.Pipeline()
    def callback(pipeline, event):
        if isinstance(event, cpp.LoadExceptionEvent):
            raise ValueError("Failed to load %s" % options.pipeline_filename)
    pipeline.add_listener(callback)
    pipeline.load(os.path.expanduser(options.pipeline_filename))
    columns = pipeline.get_measurement_columns()
    print "--- begin measurements ---"
    print "Object,Feature,Type"
    for column in columns:
        object_name, feature, data_type = column[:3]
        print "%s,%s,%s" % (object_name, feature, data_type)
    print "--- end measurements ---"
    
def print_groups(filename):
    '''Print the image set groups for this pipeline
    
    This function outputs a JSON string to the console composed of a list
    of the groups in the pipeline image set. Each element of the list is
    a two-tuple whose first element is a key/value dictionary of the
    group's key and the second is a tuple of the image numbers in the group.
    '''
    import json
    
    import cellprofiler.measurements as cpmeas
    
    path = os.path.expanduser(filename)
    m = cpmeas.Measurements(filename = path, mode="r")
    metadata_tags = m.get_grouping_tags()
    groupings = m.get_groupings(metadata_tags)
    json.dump(groupings, sys.stdout)
    
def get_batch_commands(filename):
    '''Print the commands needed to run the given batch data file headless
    
    filename - the name of a Batch_data.h5 file. The file should group image sets.
    
    The output assumes that the executable, "CellProfiler", can be used
    to run the command from the shell. Alternatively, the output could be
    run through a utility such as "sed":
    
    CellProfiler --get-batch-commands Batch_data.h5 | sed s/CellProfiler/farm_job.sh/
    '''

    import cellprofiler.measurements as cpmeas
    
    path = os.path.expanduser(filename)
    m = cpmeas.Measurements(filename = path, mode="r")
    metadata_tags = m.get_grouping_tags()
    groupings = m.get_groupings(metadata_tags)
    for grouping in groupings:
        group_string = ",".join(
            ["%s=%s" % (k,v) for k, v in grouping[0].iteritems()])
        print "CellProfiler -c -r -b -p %s -g %s" % (
            filename, group_string)
    
def run_ilastik():
    #
    # Fake ilastik into thinking it is __main__
    #
    import ilastik
    import imp
    sys.argv.remove("--ilastik")
    il_path = ilastik.__path__
    il_file, il_path, il_description = imp.find_module('ilastikMain', il_path)
    imp.load_module('__main__', il_file, il_path, il_description)

def build_extensions():
    '''Compile C and Cython files as needed'''
    import subprocess
    import cellprofiler.cpmath.setup
    import cellprofiler.utilities.setup
    from distutils.dep_util import newer_group
    #
    # Check for dependencies and compile if necessary
    #
    compile_scripts = [(os.path.join('cellprofiler', 'cpmath', 'setup.py'),
                        cellprofiler.cpmath.setup),
                       (os.path.join('cellprofiler', 'utilities', 'setup.py'),
                        cellprofiler.utilities.setup)]
    env = os.environ.copy()
    old_pythonpath = os.getenv('PYTHONPATH', None)

    # if we're using a local site_packages, the subprocesses will need
    # to be able to find it.
    
    if old_pythonpath:
        env['PYTHONPATH'] = site_packages + os.pathsep + old_pythonpath
    else:
        env['PYTHONPATH'] = site_packages

    use_mingw = (sys.platform == 'win32' and sys.version_info[0] <= 2 and
                 sys.version_info[1] <= 5)
    for compile_script, my_module in compile_scripts:
        script_path, script_file = os.path.split(compile_script)
        script_path = os.path.join(root, script_path)
        configuration = my_module.configuration()
        needs_build = False
        for extension in configuration['ext_modules']:
            target = extension.name + '.pyd'
            if newer_group(extension.sources, target):
                needs_build = True
        if not needs_build:
            continue
        if use_mingw:
            p = subprocess.Popen([sys.executable,
                                  script_file,
                                  "build_ext", "-i",
                                  "--compiler=mingw32"],
                                 cwd=script_path,
                                 env=env)
        else:
            p = subprocess.Popen([sys.executable,
                                  script_file,
                                  "build_ext", "-i"],
                                 cwd=script_path,
                                 env=env)
        p.communicate()

def run_pipeline_headless(options, args):
    '''Run a CellProfiler pipeline in headless mode'''
    
    if not options.first_image_set is None:
        if not options.first_image_set.isdigit():
            raise ValueError("The --first-image-set option takes a numeric argument")
        else:
            image_set_start = int(options.first_image_set)
    else:
        image_set_start = None
    
    image_set_numbers = None
    if not options.last_image_set is None:
        if not options.last_image_set.isdigit():
            raise ValueError("The --last-image-set option takes a numeric argument")
        else:
            image_set_end = int(options.last_image_set)
            if image_set_start is None:
                image_set_numbers = np.arange(1, image_set_end+1)
            else:
                image_set_numbers = np.arange(image_set_start, image_set_end+1)
    else:
        image_set_end = None
    
    if ((options.pipeline_filename is not None) and 
        (not options.pipeline_filename.lower().startswith('http'))):
        options.pipeline_filename = os.path.expanduser(options.pipeline_filename)
    from cellprofiler.pipeline import Pipeline, EXIT_STATUS, M_PIPELINE
    import cellprofiler.measurements as cpmeas
    pipeline = Pipeline()
    initial_measurements = None
    try:
        if h5py.is_hdf5(options.pipeline_filename):
            initial_measurements = cpmeas.load_measurements(
                options.pipeline_filename,
                image_numbers=image_set_numbers)
    except:
        logging.root.info("Failed to load measurements from pipeline")
    if initial_measurements is not None:
        pipeline_text = \
            initial_measurements.get_experiment_measurement(
                M_PIPELINE)
        pipeline_text = pipeline_text.encode('us-ascii')
        pipeline.load(StringIO(pipeline_text))
        if not pipeline.in_batch_mode():
            #
            # Need file list in order to call prepare_run
            #
            from cellprofiler.utilities.hdf5_dict import HDF5FileList
            with h5py.File(options.pipeline_filename, "r") as src:
                if HDF5FileList.has_file_list(src):
                    HDF5FileList.copy(
                        src, initial_measurements.hdf5_dict.hdf5_file)
    else:
        pipeline.load(options.pipeline_filename)
    if options.groups is not None:
        kvs = [x.split('=') for x in options.groups.split(',')]
        groups = dict(kvs)
    else:
        groups = None
    use_hdf5 = len(args) > 0 and not args[0].lower().endswith(".mat")
    measurements = pipeline.run(
        image_set_start=image_set_start, 
        image_set_end=image_set_end,
        grouping=groups,
        measurements_filename = None if not use_hdf5 else args[0],
        initial_measurements = initial_measurements)
    if len(args) > 0 and not use_hdf5:
        pipeline.save_measurements(args[0], measurements)
    if options.done_file is not None:
        if (measurements is not None and 
            measurements.has_feature(cpmeas.EXPERIMENT, EXIT_STATUS)):
            done_text = measurements.get_experiment_measurement(EXIT_STATUS)
        else:
            done_text = "Failure"
        fd = open(options.done_file, "wt")
        fd.write("%s\n"%done_text)
        fd.close()
    if measurements is not None:
        measurements.close()
    
if __name__ == "__main__":
    main(sys.argv)
    os._exit(0)
