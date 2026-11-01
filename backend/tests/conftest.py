import os
import tempfile
# Set test storage before any test module imports the application engine.
os.environ['DATA_DIR']=tempfile.mkdtemp(prefix='lia-test-suite-')
