import logging
import os
from typing import List

import documentation.scripts.render_md as rmd
import helpers.unit_test as ut

_LOG = logging.getLogger(__name__)
# #############################################################################


class Test_render_md1(ut.TestCase):
    """Test _uml_file_names method that returns output pathes"""

    def test_uml_file_names1(self) -> None:
        """
        Check output dir and file names correctness for absolute
        destination path.
        """
        dest_file = "/a/b/c/d/e.md"
        idx = 8
        extension = "png"
        pathes = rmd._uml_file_names(dest_file, idx, extension)
        self.check_string("\n".join(pathes))


class Test_render_md2(ut.TestCase):
    """Test _render_command method that construct plantuml command"""

    def test_render_command1(self) -> None:
        """
        Check correctness of the command to render.
        """
        uml_file = "/a/b/c.puml"
        dest = "/d/e/f"
        extension = "png"
        cmd = rmd._render_command(uml_file, dest, extension)
        self.check_string(cmd)

    def test_render_command2(self) -> None:
        """
        Check assertion if extension is unknown when render command is building.
        """
        uml_file = "/a/b/c.puml"
        dest = "/d/e/f"
        extension = "bmp"
        with self.assertRaises(AssertionError) as cm:
            rmd._render_command(uml_file, dest, extension)
        # Check error text.
        self.assertIn("bmp", str(cm.exception))


class Test_render_md3(ut.TestCase):
    """Test _render_plantuml method that adds strings with links to rendered images"""

    def test_render_plantuml1(self) -> None:
        """
        Check correctness of rendering just UML text.
        """
        in_text = [
            "```plantuml",
            "Alice --> Bob",
            "```",
        ]
        self._check_str_after_render(in_text)

    def test_render_plantuml2(self) -> None:
        """
        Check correctness of rendering UML with another text.
        """
        in_text = [
            "A",
            "```plantuml",
            "Alice --> Bob",
            "```",
            "B",
        ]
        self._check_str_after_render(in_text)

    def test_render_plantuml3(self) -> None:
        """
        Check correctness of rendering text without UML.
        """
        in_text = [
            "A",
            "```bash",
            "Alice --> Bob",
            "```",
            "B",
        ]
        self._check_str_after_render(in_text)

    def test_render_plantuml4(self) -> None:
        """
        Check correctness of rendering UML text already pre-formatted.
        """
        in_text = [
            "```plantuml",
            "@startuml",
            "Alice --> Bob",
            "@enduml",
            "```",
        ]
        self._check_str_after_render(in_text)

    def test_render_plantuml_playback1(self) -> None:
        """Test real usage for vendors2/kibot/instrument_master_architecture.md"""
        # Define input variables
        in_txt = [
            "<!--ts-->",
            "   * [Overview](#overview)",
            "   * [Architecture](#architecture)",
            "      * [System context diagram](#system-context-diagram)",
            "      * [Container Diagram](#container-diagram)",
            "         * [Questions](#questions)",
            "         * [Notes](#notes)",
            "   * [Data Model](#data-model)",
            "      * [Notes](#notes-1)",
            "   * [Proposed Code Layout](#proposed-code-layout)",
            "      * [Guidelines](#guidelines)",
            "      * [Questions](#questions-1)",
            "",
            "",
            "",
            "<!--te-->",
            "",
            "# Overview",
            "",
            "At a high level, we want to implement a system that:",
            "",
            "- Downloads the price data (both historical & also real-time) from different",
            "  data sources (we already have Kibot interface and want to add an interface for",
            "  EODData)",
            "- Downloads and saves the related metadata",
            "- Convert CSV price data into a suitable format for fast querying (e.g., Parquet",
            "  format)",
            "- Implement mapping between metadata and price data",
            "- Allow to query the system to get specific price time series based on symbol",
            "  name",
            "  - It should handle:",
            "    - Different frequency (e.g., end-of-day vs 5 minutes vs 1 minute)",
            "    - Different asset classes (e.g., equities vs futures vs forex vs ...)",
            "    - Different providers (e.g., `kibot` vs `eoddata` vs `firstrate` vs ...)",
            "  - This system has:",
            "    - Different backends for different data providers (e.g., Kibot, EODData)",
            "    - A layer to make all the data uniform from the semantics point of view",
            "",
            "# Architecture",
            "",
            "Note: The documentation of the architecture follows the C4 model:",
            "https://c4model.com/.",
            "",
            "## System context diagram",
            "",
            "```plantuml",
            "@startuml",
            "title System Context Diagram",
            "",
            "skinparam defaultTextAlignment center",
            "skinparam component {",
            "    backgroundcolor<<main>> RoyalBlue",
            "    FontColor<<main>> white",
            "}",
            "",
            "component imaster <<main>> [",
            "**Instrument Master**",
            "",
            "Implements an ETL pipeline that fetches stock data from",
            "different vendors, and provides stock data & metadata",
            "in standardized formats.",
            "]",
            "",
            "component vendors [",
            "**Stock Data Vendors**",
            "",
            "i.e: Kibot, Eoddata, ...",
            "]",
            "",
            "component models [",
            "**Data Analysis Models**",
            "",
            "ML Models that process the structured data from instrument",
            "master and produce insights.",
            "]",
            "",
            "imaster -up-> vendors: fetches raw data from",
            "imaster <-- models: fetches processed data from",
            "@enduml",
            "```",
            "![](plantuml-images/instrument_master_architecture.1.png)",
            "",
            "## Container Diagram",
            "",
            "```plantuml",
            "@startuml",
            "title Container Diagram",
            "",
            "skinparam defaultTextAlignment center",
            "",
            'package "Instrument Master" {',
            '   package "Vendor ETL Pipeline" {',
            "      component vextractor [",
            "      **Vendor Extractor**",
            "",
            "      Extracts data from the vendor",
            "      (one for each vendor)",
            "      ]",
            "",
            "      component vtransformer [",
            "      **Vendor Transformer**",
            "",
            "      Transforms csv data into standardized pq format",
            "      (one for each vendor)",
            "      ]",
            "",
            "      component vloader [",
            "      **Vendor Loader**",
            "",
            "      Loads data from standardized pq format",
            "      - can perform light transformation",
            "      ]",
            "",
            "   }",
            "",
            "    component loader [",
            "    **Loader**",
            "",
            "    Loads data from standardized pq format",
            "    (not vendor specific)",
            "    ]",
            "",
            "    database objstore [",
            "    **Object Store**",
            "",
            "    local file system or s3",
            "    ]",
            "",
            "    vextractor -down-> objstore: sends extracted data",
            "    vtransformer <-right-> objstore: reads extracted data\\lwrite transofrmed data",
            "    vloader -up-> objstore: read transoformed data",
            "    loader -up-> vloader: read standardized (parquet) data",
            "",
            "    ' styling",
            "    vextractor -[hidden]down- vtransformer",
            "    vtransformer -[hidden]down- vloader",
            "",
            "}",
            "",
            "component vendors [",
            "Stock Data Vendors",
            "",
            "i.e: Kibot, Eoddata, ...",
            "]",
            "",
            "component models [",
            "Data analysis models",
            "",
            "ML Models that process the structured data from instrument",
            "master and produce insights.",
            "]",
            "",
            "vendors <-- vextractor: fetches data from",
            "loader <-up- models: fetches data from",
            "@enduml",
            "```",
            "![](plantuml-images/instrument_master_architecture.2.png)",
            "",
            "### Questions",
            "",
            "1. How does each stage in the container diagram run? are they all manually",
            "   triggered? this view implies that these stages run independently, which I",
            "   believe is desired, but we could also use a sequence diagram to highlight how",
            "   these should be triggered.",
            "",
            "TODO(Amr): Add a sequence diagram later",
            "",
            "> GP: We will run the extractor and transformer only once to generate historical",
            "> data.",
            ">",
            "> Later we will implement a real-time processor (e.g., with Airflow) that keeps",
            "> the data updated. The interface of course won't change",
            "",
            "### Notes",
            "",
            "- I didn't reflect caching in this diagram just yet",
            "- `data` refers to both stock data & metadata in this context",
            "- The vendor loader can do light transformation because we may need to test out",
            "  some transformation steps, and the transformer step is sometimes too costly to",
            "  allow that.",
            "",
            "TODO(Amr): think if there's a better way to handle this, perhaps caching could",
            "help mitigate these costier steps, and transformation doesn't need to be a",
            "single step.",
            "",
            "# Data Model",
            "",
            "```plantuml",
            "@startuml",
            "title Data Model",
            "",
            "hide enum methods",
            "hide class methods",
            "",
            "namespace base {",
            "   enum AssetClass {",
            "      Futures",
            "      Stocks",
            "      ETFs",
            "   }",
            "",
            "   class Exchange {",
            "      Name: str",
            "   }",
            "",
            "   class Symbol {",
            "      Code: str",
            "      Description: str",
            "      AssetClass: AssetClass",
            "      Start_date: date",
            "      SymbolBase: str",
            "   }",
            "",
            "   class TradedSymbol {",
            "      symbol: Symbol",
            "      exchange: Exchange",
            "   }",
            "",
            "   Symbol -up-> AssetClass: A symbol has\\lan asset class",
            "   Symbol -up-> TradedSymbol: A symbol can be traded\\lin multiple exchanges",
            "   Exchange -down-> TradedSymbol: An exchange contains\\lmultiple symbols",
            "}",
            "",
            "namespace data {",
            "   class MinuteData {",
            "      traded_symbol: TradedSymbol",
            "      datetime: datetime",
            "      Open: float",
            "      High: float",
            "      Low: float",
            "      Close: float",
            "      Volume: int",
            "   }",
            "",
            "   class TickData {",
            "      traded_symbol: TradedSymbol",
            "      datetime: datetime",
            "      Bid: float",
            "      Ask: float",
            "      Volume: int",
            "   }",
            "",
            "   MinuteData -left-> base.TradedSymbol",
            "   TickData -left-> base.TradedSymbol",
            "",
            "}",
            "",
            "namespace metadata {",
            "   class SymbolChange {",
            "      old_symbol: Symbol",
            "      new_symbol: Symbol",
            "      datetime: datetime",
            "   }",
            "",
            "   class TickBidAskContractMetaData {",
            "      traded_symbol: TradedSymbol",
            "      start_date: date",
            "      size: float",
            "      Description: str",
            "   }",
            "",
            "   class MarketSession {",
            "      Type: str",
            "      Start_time: time",
            "      End_time: time",
            "      traded_symbol: TradedSymbol",
            "   }",
            "",
            "   SymbolChange -up-> base.Symbol",
            "   TickBidAskContractMetaData -up-> base.TradedSymbol",
            "   MarketSession -up-> base.TradedSymbol",
            "}",
            "",
            "namespace generated {",
            "   class AggregateTickData {",
            "      traded_symbol: TradedSymbol",
            "      data: date",
            "      bid_open: float",
            "      bid_high: float",
            "      bid_low: float",
            "      bid_close: float",
            "      ask_open: float",
            "      ask_high: float",
            "      ask_low: float",
            "      ask_close: float",
            "   }",
            "",
            "   AggregateTickData -left-> data.TickData",
            "}",
            "@enduml",
            "```",
            "![](plantuml-images/instrument_master_architecture.3.png)",
            "",
            "## Notes",
            "",
            "- Generated data should be behind an interface (then it computed on the fly or",
            "  cached somehow).",
            "",
            "# Proposed Code Layout",
            "",
            "Based on the container diagram, the code layout matches the different containers",
            "that we have.",
            "",
            "```ansi",
            "types/  # standardized types (see data model above)",
            "loader/  # adapts all vendor loaders to a common interface",
            "vendors/",
            "   kibot/",
            "      extractor/",
            "      transformer/",
            "      loader/",
            "      types/  # vendor specific types",
            "      config.py  # s3 paths, credentials for vendor",
            "   eoddata/",
            "      extractor/",
            "      transformer/",
            "      loader/",
            "      types/",
            "      config.py",
            "```",
            "",
            "## Guidelines",
            "",
            "- `extractor` should only download the data, and keep it as close to the",
            "  downloaded structure as possible (ideally not modify it at all.)",
            "- Downloading already downloaded data should be a no-op by default (before",
            "  downloading, check that the file doesn't exist in s3). This behavior should be",
            "  overridable by a command line arg: `--override` (which is the opposite of",
            "  `--incremental`)",
            "- `extractor` & `transformer` share certain types, and s3 paths (where",
            "  `extractor` outputs files and `transformer` picks them up), those would be",
            "  saved in `config.py`",
            "- We should make a distinction between `data` & `metadata` in all of the",
            "  packages.",
            "",
            "TODO(Amr): be more specific about how to make that distinction",
            "",
            "## Questions",
            "",
            "1. For the `extractor` package, should these be individual runnable scripts? or",
            "   should we have a `download all` script/command?",
            "",
            "> **GP:** I would do individual scripts, since this for now is a one-off",
            "> operation and we will download data in chunks",
            ">",
            "> I'm also ok with a single script with --dataset to control which subset of the",
            "> data to download / transform",
            "",
            "2. Should we have a coverage matrix for which data each vendor fulfills?",
            "",
            "> **GP:**: Not urgent",
            "",
        ]
        out_file = "vendors2/kibot/instrument_master_architecture.md"
        extension = "png"
        dry_run = True
        # Call function to test
        act = rmd._render_plantuml(
            in_txt=in_txt, out_file=out_file, extension=extension, dry_run=dry_run
        )
        act = str(act)
        # Check output
        self.check_string(act)

    def _check_str_after_render(self, in_text: List[str]) -> None:
        out_file = os.path.join(self.get_scratch_space(), "out.md")
        extension = "png"
        out_text = rmd._render_plantuml(
            in_text, out_file, extension, dry_run=True
        )
        self.check_string("\n".join(out_text))
