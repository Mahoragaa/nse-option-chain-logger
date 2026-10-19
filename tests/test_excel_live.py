import sys
import types
from pathlib import Path

from nse_oi_logger.excel_live import ExcelLiveWorkbook, _UpdateRequest


def test_excel_live_reconnects_after_com_disconnect(monkeypatch, tmp_path):
    dispatches = []
    update_attempts = []

    class FakeWorkbook:
        def Save(self):
            return None

        def Close(self, SaveChanges):
            assert SaveChanges is True
            return None

    class FakeExcel:
        Visible = False
        DisplayAlerts = True

        def __init__(self):
            self.workbook = FakeWorkbook()
            self.Workbooks = self

        def Open(self, path):
            assert Path(path).name.endswith(".xlsx")
            return self.workbook

        def Quit(self):
            return None

    client_module = types.ModuleType("win32com.client")

    def dispatch_excel(_application):
        assert _application == "Excel.Application"
        dispatches.append(True)
        return FakeExcel()

    client_module.DispatchEx = dispatch_excel
    win32com_module = types.ModuleType("win32com")
    win32com_module.client = client_module
    pythoncom_module = types.ModuleType("pythoncom")
    pythoncom_module.CoInitialize = lambda: None
    pythoncom_module.CoUninitialize = lambda: None
    monkeypatch.setitem(sys.modules, "pythoncom", pythoncom_module)
    monkeypatch.setitem(sys.modules, "win32com", win32com_module)
    monkeypatch.setitem(sys.modules, "win32com.client", client_module)

    def fail_once(_workbook, _rows):
        assert isinstance(_rows, dict)
        assert hasattr(_workbook, "Save")
        update_attempts.append(True)
        if len(update_attempts) == 1:
            raise Exception(-2147417848, "The object invoked has disconnected from its clients.")

    monkeypatch.setattr(ExcelLiveWorkbook, "_update_workbook", staticmethod(fail_once))

    publisher = ExcelLiveWorkbook(tmp_path)
    publisher._workbook_path = tmp_path / "OptionChain_NIFTY_2026-10-19.xlsx"
    request = _UpdateRequest(publisher._workbook_path, {})
    publisher._requests.put(request)
    publisher._requests.put(None)

    publisher._run()

    assert request.completed.is_set()
    assert request.error is None
    assert len(update_attempts) == 2
    assert len(dispatches) == 2


def test_live_workbook_centers_newly_added_rows():
    class FakeRange:
        HorizontalAlignment = None
        Value = None

        def AutoFilter(self):
            return None

    class FakeCells:
        def ClearContents(self):
            return None

        def __call__(self, row, column):
            return row, column

    class FakeSheet:
        def __init__(self, name):
            self.Name = name
            self.Cells = FakeCells()
            self.ranges = []
            self.Columns = lambda _columns: types.SimpleNamespace(AutoFit=lambda: None)

        def Range(self, _start, _end):
            result = FakeRange()
            self.ranges.append(result)
            return result

        def Activate(self):
            return None

        def Delete(self):
            return None

    class FakeWorksheets:
        def __init__(self):
            self.sheets = [FakeSheet("Summary")]

        def __iter__(self):
            return iter(self.sheets)

        def __call__(self, name):
            if isinstance(name, int):
                return self.sheets[name - 1]
            return next(sheet for sheet in self.sheets if sheet.Name == name)

        @property
        def Count(self):
            return len(self.sheets)

        def Add(self, After):
            assert After is self.sheets[-1]
            sheet = FakeSheet("")
            self.sheets.append(sheet)
            return sheet

    workbook = types.SimpleNamespace(
        Worksheets=FakeWorksheets(),
        Application=types.SimpleNamespace(
            ActiveWindow=types.SimpleNamespace(SplitRow=None, FreezePanes=None)
        ),
        Save=lambda: None,
    )
    rows = {(23000, "2026-10-19"): [
        {"time_slot": "13:51:00", "strike": 23000, "call_oi": 1},
    ]}

    ExcelLiveWorkbook._update_workbook(workbook, rows)

    data_sheet = workbook.Worksheets("23000_2026-10-19")
    assert any(item.HorizontalAlignment == -4108 for item in data_sheet.ranges)
