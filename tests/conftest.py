import sys
import types
from pathlib import Path


package = types.ModuleType("epson_labelworks")
package.__path__ = [str(Path(__file__).parents[1] / "custom_components" / "epson_labelworks")]
sys.modules["epson_labelworks"] = package
