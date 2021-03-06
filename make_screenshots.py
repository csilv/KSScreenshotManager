#!/usr/bin/python
# Usage: python make_screenshots.py /path/to/screenshot/output
# This script will create the output directory if necessary.

import os
import re
import sys
import subprocess
import glob
import argparse
import json
import shutil

XCODE_BUILD_DIR = os.path.expanduser('~/Library/Developer/Xcode/DerivedData')

def compile_iossim():
    previous_dir = os.getcwd()
    os.chdir(os.path.join(os.path.realpath(os.path.split(__file__)[0]), 'Contributed', 'ios-sim'))
    subprocess.call(['xcodebuild', '-scheme', 'ios-sim', '-configuration', 'Release', 'clean', 'build', 'SYMROOT=build'], stdout=open('/dev/null', 'w'))
    os.chdir(previous_dir)

def compile_app():
    previous_dir = os.getcwd()
    os.chdir(project_path)
    
    # Force the simulator build to use 32-bit, otherwise UIGetScreenImage doesn't exist
    if options.has_key('workspace'):
        subprocess.call(['xcodebuild', '-workspace', options['workspace'], '-scheme', options['scheme'], '-configuration', options['build_config'], '-sdk', 'iphonesimulator', 'clean', 'build', 'ARCHS=i386', 'ONLY_ACTIVE_ARCH=NO'], stdout=open('/dev/null', 'w'))
    else:
        subprocess.call(['xcodebuild', '-target', options['target_name'], '-configuration', options['build_config'], '-sdk', 'iphonesimulator', 'clean', 'build', 'ARCHS=i386', 'ONLY_ACTIVE_ARCH=NO'], stdout=open('/dev/null', 'w'))
    os.chdir(previous_dir)

def quit_simulator():
    subprocess.call(['killall', 'iPhone Simulator'])
    
def reset_simulator():
    shutil.rmtree(os.path.expanduser('~/Library/Application Support/iPhone Simulator'), ignore_errors=True)

def iossim(app_path, args, device):
    subprocess_args = ['ios-sim', 'launch', app_path]

    # ios-sim does the default setting itself, so convert the device name into arguments that ios-sim expects
    if 'iPad' in device:
        subprocess_args += ['--family', 'ipad']
    else:
        subprocess_args += ['--family', 'iphone']

    if 'Retina' in device:
        subprocess_args += ['--retina']

    if '(4-inch)' in device:
        subprocess_args += ['--tall']

    subprocess_args += ['--args']
    subprocess_args += args
    
    subprocess.call(subprocess_args)

def appBuildDir(project_path):
    project_name = None
    for d in os.listdir(project_path):
        result = re.match('(\w+)\.xcodeproj', d)
        if os.path.isdir(os.path.join(project_path, d)) and result:
            project_name = result.group(1)
            break
    if not project_name:
        print 'No XCode project found at ' + project_path
        exit()

    for d in os.listdir(XCODE_BUILD_DIR):
        if os.path.isdir(os.path.join(XCODE_BUILD_DIR, d)) and d.find(project_name) > -1:
           return d
    print 'No built project found for ' + project_name
    exit()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build iOS screenshots.')
    parser.add_argument('--path', '-p', dest='destination', help='destination path for screenshots (overrides config)')
    parser.add_argument('config', help='path to JSON config file')

    args = parser.parse_args()
    config_path = args.config

    ###
    # Read in configuration file
    ###

    try:
        options = json.load(open(config_path))
    except IOError:
        print 'Configuration file not found at ' + config_path
        exit()
    except ValueError:
        print "Syntax error in JSON file."
        exit()

    if args.destination:
        options['destination_path'] = args.destination

    ###

    if os.path.isabs(os.path.expanduser(options['destination_path'])):
        destination_path = os.path.expanduser(options['destination_path'])
    else:
        # destination_path is relative to the parent directory of config_path
        destination_path = os.path.realpath(os.path.join(os.path.dirname(config_path), options['destination_path']))

    if os.path.isabs(options['project_path']):
        project_path = options['project_path']
    else:
        # project_path is relative to the parent directory of config_path
        project_path = os.path.realpath(os.path.join(os.path.dirname(config_path), options['project_path']))

    # If no target or workspace is specified, assume the app has already been compiled manually by XCode
    if options.has_key('workspace') or options.has_key('target_name'):
        print 'Building with ' + options['build_config'] + ' configuration...'
        compile_app()

    app_path = os.path.join(XCODE_BUILD_DIR, appBuildDir(project_path), 'Build/Products', options['build_config'] + '-iphonesimulator', options['app_name'])

    # create destination directory
    if not os.path.exists(destination_path):
        os.makedirs(destination_path)

    for device in options['devices']:
        quit_simulator()

        for language in options['languages']:
            language_path = os.path.join(destination_path, language)
            locale = language
            if not os.path.exists(language_path):
                os.makedirs(language_path)

            if language == "pt-BR":
              language = "pt"

            print 'Creating screenshots for {} using {}...'.format(language, device)

            if 'reset_between_runs' in options and options['reset_between_runs']:
                quit_simulator()
                reset_simulator()

            iossim(app_path, ['-AppleLanguages', '({})'.format(language), '-AppleLocale', locale, language_path], device)

    quit_simulator()
