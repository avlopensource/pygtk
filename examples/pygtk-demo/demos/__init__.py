
import os

_file_list = [
    x for x in os.listdir(os.path.dirname(__file__))
    if len(x) > 3 and x[-3:] == '.py']

demo_list = []
for _mod in _file_list:
    # Leave underscored Modulnames.
    if _mod.startswith('_'):
        continue
    _mod = _mod[:-3]
    try:
        _doc = ''
        exec('from . import ' + _mod + '\n' + \
        '_doc = ' + _mod + '.__doc__')
        if '_doc' is not None:
            _description = _doc.splitlines()[0]
        else:
            _description = 'No description for {}'.format(_mod)
        demo_list.append((_description, _mod))
    except (ImportError, AttributeError, TabError) as msg:
        # ImportError or AttributeError (if _doc is None)
        #print 'failed: ', _mod
        pass

demo_list.sort()
