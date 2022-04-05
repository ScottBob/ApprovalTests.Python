import xml.dom.minidom
from pathlib import Path
from typing import Callable, List, Optional, Any, ByteString

import approvaltests.reporters.default_reporter_factory
from approvaltests.utils import to_json
from approvaltests.approval_exception import ApprovalException
from approvaltests.binary_writer import BinaryWriter
from approvaltests.core import Reporter, Writer
from approvaltests.namer.namer_base import NamerBase
from approvaltests.namer.stack_frame_namer import StackFrameNamer
from approvaltests.core.options import Options
from approvaltests.core.scenario_namer import ScenarioNamer
from approvaltests.existing_file_writer import ExistingFileWriter
from approvaltests.file_approver import FileApprover
from approvaltests.list_utils import format_list
from approvaltests.reporters.diff_reporter import DiffReporter
from approvaltests.string_writer import StringWriter

__unittest = True
__tracebackhide__ = True


def set_default_reporter(reporter: Reporter) -> None:
    return approvaltests.reporters.default_reporter_factory.set_default_reporter(reporter)


def get_default_reporter() -> Reporter:
    return approvaltests.reporters.default_reporter_factory.get_default_reporter()


def get_reporter(reporter: Optional[Reporter]) -> Reporter:
    return approvaltests.reporters.default_reporter_factory.get_reporter(reporter)


def get_default_namer(extension: Optional[str] = None) -> StackFrameNamer:
    return approvaltests.namer.default_namer_factory.get_default_namer(extension)


def verify(
    data: Any,
    reporter: Optional[Reporter] = None,
    namer: Optional[NamerBase] = None,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
    *,  # enforce keyword arguments - https://www.python.org/dev/peps/pep-3102/
    options: Optional[Options] = None
) -> None:
    """Verify string data against a previously approved version of the string.

    Args:
        data: A string containing the data to be compared with approved data from a previous run.
            On Python 2 this can be a bytes, str, or unicode object. On Python 3 this should be
            a str object.

        reporter: An optional Reporter. If None (the default), the default reporter
            will be used; see get_default_reporter().

        encoding: An optional encoding to be used when serialising the data to a byte stream for
            comparison. If None (the default) a locale-dependent encoding will be used; see
            locale.getpreferredencoding().

        errors: An optional string that specifies how encoding and decoding errors are to be handled
            If None (the default) or 'strict', raise a ValueError exception if there is an encoding
            error. Pass 'ignore' to ignore encoding errors. Pass 'replace' to use a replacement
            marker (such as '?') when there is malformed data.

        newline: An optional string that controls how universal newlines work when comparing data.
            It can be None, '', '\n', '\r', and '\r\n'. If None (the default) universal newlines are
            enabled and any '\n' characters are translated to the system default line separator
            given by os.linesep. If newline is '', no translation takes place. If newline is any of
            the other legal values, any '\n' characters written are translated to the given string.

    Raises:
        ApprovalException: If the verification fails because the given string does not match the
            approved string.

        ValueError: If data cannot be encoded using the specified encoding when errors is set to
            None or 'strict'.
    """
    options = initialize_options(options, reporter)
    namer_to_use = namer or options.namer
    verify_with_namer(
        data,
        namer_to_use,
        encoding=encoding,
        errors=errors,
        newline=newline,
        options=options,
    )


def verify_binary(
    data: ByteString,
    file_extension_with_dot: str,
    *,  # enforce keyword arguments - https://www.python.org/dev/peps/pep-3102/
    options: Optional[Options] = None
) -> None:
    options = initialize_options(options, None).for_file.with_extension(file_extension_with_dot)
    verify_with_namer_and_writer(
        options.namer,
        BinaryWriter(data, file_extension_with_dot),
        None,
        options=options
    )


def initialize_options(
    options: Optional[Options], reporter: Optional[Reporter] = None
) -> Options:
    if options is None:
        options = Options()
    if reporter is not None:
        options = options.with_reporter(reporter)
    return options


def verify_with_namer(
    data: Any,
    namer: NamerBase,
    reporter: Optional[Reporter] = None,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
    *,  # enforce keyword arguments - https://www.python.org/dev/peps/pep-3102/
    options: Optional[Options] = None
) -> None:
    """Verify string data against a previously approved version of the string.

    Args:
        data: A string containing the data to be compared with approved data from a previous run.
            On Python 2 this can be a bytes, str, or unicode object. On Python 3 this should be
            a str object.

        namer: A Namer instance used for naming approved and received data files.

        reporter: An optional Reporter. If None (the default), the default reporter
            will be used; see get_default_reporter().

        encoding: An optional encoding to be used when serialising the data to a byte stream for
            comparison. If None (the default) a locale-dependent encoding will be used; see
            locale.getpreferredencoding().

        errors: An optional string that specifies how encoding and decoding errors are to be handled
            If None (the default) or 'strict', raise a ValueError exception if there is an encoding
            error. Pass 'ignore' to ignore encoding errors. Pass 'replace' to use a replacement
            marker (such as '?') when there is malformed data.

        newline: An optional string that controls how universal newlines work when comparing data.
            It can be None, '', '\n', '\r', and '\r\n'. If None (the default) universal newlines are
            enabled and any '\n' characters are translated to the system default line separator
            given by os.linesep. If newline is '', no translation takes place. If newline is any of
            the other legal values, any '\n' characters written are translated to the given string.

    Raises:
        ApprovalException: If the verification fails because the given string does not match the
            approved string.

        ValueError: If data cannot be encoded using the specified encoding when errors is set to
            None or 'strict'.
    """
    options = initialize_options(options, reporter)
    writer = StringWriter(
        options.scrub(str(data)), encoding=encoding, errors=errors, newline=newline
    )
    verify_with_namer_and_writer(namer, writer, options=options)


def verify_with_namer_and_writer(
    namer: NamerBase,
    writer: Writer,
    reporter: Optional[Reporter]= None,
    *,  # enforce keyword arguments - https://www.python.org/dev/peps/pep-3102/
    options: Optional[Options] = None
) -> None:
    options = initialize_options(options, reporter)
    approver = FileApprover()
    error = approver.verify(namer, writer, options.reporter, options.comparator)
    if error:
        raise ApprovalException(error)


def verify_as_json(
    object,
    reporter=None,
    *,  # enforce keyword arguments - https://www.python.org/dev/peps/pep-3102/
    deserialize_json_fields = False,
    options: Optional[Options] = None
):
    if deserialize_json_fields:
        object = approvaltests.utils.deserialize_json_fields(object)
    options = initialize_options(options, reporter)
    n_ = to_json(object) + "\n"
    verify(n_, None, encoding="utf-8", newline="\n", options=options)


def verify_xml(
    xml_string: str,
    reporter: None = None,
    namer: NamerBase = None,
    *,  # enforce keyword arguments - https://www.python.org/dev/peps/pep-3102/
    options: Optional[Options] = None
) -> None:
    options = initialize_options(options, reporter)
    try:
        dom = xml.dom.minidom.parseString(xml_string)
        pretty_xml = dom.toprettyxml()
    except Exception:
        pretty_xml = xml_string

    verify(pretty_xml, options=options.for_file.with_extension(".xml"))

def verify_html(
    html_string: str,
    *,  # enforce keyword arguments - https://www.python.org/dev/peps/pep-3102/
    options: Optional[Options] = None
) -> None:
    options = initialize_options(options)
    try:
        from bs4 import BeautifulSoup
        pretty_html = BeautifulSoup(html_string, 'html.parser').prettify()
    except Exception:
        pretty_html = html_string

    verify(pretty_html, options=options.for_file.with_extension(".html"))


def verify_file(
    file_name: str,
    reporter: Reporter = None,
    *,  # enforce keyword arguments - https://www.python.org/dev/peps/pep-3102/
    options: Optional[Options] = None
) -> None:
    """Verify the contents of a text file against previously approved contents.

    Args:
        file_name: The path to a file. The file will be opened in text mode.

        reporter: An optional Reporter. If None (the default), the default reporter
            will be used; see get_default_reporter().


    Raises:
        ApprovalException: If the verification fails because the given string does not match the
            approved string.

        ValueError: If data cannot be encoded using the specified encoding when errors is set to
            None or 'strict'.
    """
    options = initialize_options(options, reporter)
    options = options.for_file.with_extension(Path(file_name).suffix, no_override = True)
    verify_with_namer_and_writer(
        options.namer, ExistingFileWriter(file_name, options), None, options=options
    )

def verify_all(
    header: str,
    alist: List[str],
    formatter: Optional[Callable] = None,
    reporter: Optional[DiffReporter] = None,
    encoding: None = None,
    errors: None = None,
    newline: None = None,
    *,  # enforce keyword arguments - https://www.python.org/dev/peps/pep-3102/
    options: Optional[Options] = None
) -> None:
    """Verify a collection of items against a previously approved collection.

    Args:
        header: A header line string to be included before the list of items.

        alist: An iterable series of objects, a string representation of each of which will be
            included in an aggregated string for comparison.

        formatter: An optional object which must have a print_item(x) method such that
            formatter.print_item(x) will return a string representation of a single item from alist.

        reporter: An optional Reporter. If None (the default), the default reporter
            will be used; see get_default_reporter().

        encoding: An optional encoding to be used when serialising the data to a byte stream for
            comparison. If None (the default) a locale-dependent encoding will be used; see
            locale.getpreferredencoding().

        errors: An optional string that specifies how encoding and decoding errors are to be handled
            If None (the default) or 'strict', raise a ValueError exception if there is an encoding
            error. Pass 'ignore' to ignore encoding errors. Pass 'replace' to use a replacement
            marker (such as '?') when there is malformed data.

        newline: An optional string that controls how universal newlines work when comparing data.
            It can be None, '', '\n', '\r', and '\r\n'. If None (the default) universal newlines are
            enabled and any '\n' characters are translated to the system default line separator
            given by os.linesep. If newline is '', no translation takes place. If newline is any of
            the other legal values, any '\n' characters written are translated to the given string.

    Raises:
        ApprovalException: If the verification fails because the given string does not match the
            approved string.

        ValueError: If data cannot be encoded using the specified encoding when errors is set to
            None or 'strict'.
    """
    options = initialize_options(options, reporter)
    text = format_list(alist, formatter, header)
    verify(
        text, None, encoding=encoding, errors=errors, newline=newline, options=options
    )


def get_scenario_namer(scenario_name: int) -> ScenarioNamer:
    return ScenarioNamer(get_default_namer(), scenario_name)


def delete_approved_file():
    filename = Path(get_default_namer().get_approved_filename())
    if filename.exists():
        filename.unlink()
