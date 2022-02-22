import os
from typing import Tuple

from orbis.data.misc import Context
from orbis.data.results import CommandData
from orbis.data.schema import Build, Test
from orbis.ext.database import TestOutcome
from orbis.handlers.command import CommandHandler
from xml.etree.ElementTree import parse


def _remove_test_results(project_dir):
    for r, dirs, files in os.walk(project_dir):
        for file in files:
            filePath = os.path.join(r, file)
            if ("target/surefire-reports" in filePath or "target/failsafe-reports" in filePath
                or "build/test-results" in filePath) and file.endswith('.xml') and file.startswith('TEST-'):
                os.remove(filePath)


def _read_test_results(project_dir):
    surefire_report_files = []
    for r, dirs, files in os.walk(project_dir):
        for file in files:
            filePath = os.path.join(r, file)
            if ("target/surefire-reports" in filePath or "target/failsafe-reports" in filePath
                or "build/test-results" in filePath) and file.endswith('.xml') and file.startswith('TEST-'):
                surefire_report_files.append(filePath)

    failing_tests_count = 0
    error_tests_count = 0
    passing_tests_count = 0
    skipping_tests_count = 0

    passingTestCases = set()
    skippingTestCases = set()
    failingTestCases = set()

    failures = []

    for report_file in surefire_report_files:
        with open(report_file, 'r') as file:
            xml_tree = parse(file)
            testsuite_class_name = xml_tree.getroot().attrib['name']
            test_cases = xml_tree.findall('testcase')
            for test_case in test_cases:
                failure_list = {}
                class_name = test_case.attrib[
                    'classname'] if 'classname' in test_case.attrib else testsuite_class_name
                method_name = test_case.attrib['name']
                failure_list['test_class'] = class_name
                failure_list['test_method'] = method_name

                failure = test_case.findall('failure')
                if len(failure) > 0:
                    failing_tests_count += 1
                    failure_list['failure_name'] = failure[0].attrib['type']
                    if 'message' in failure[0].attrib:
                        failure_list['detail'] = failure[0].attrib['message']
                    failure_list['is_error'] = False
                    failures.append(failure_list)
                    failingTestCases.add(class_name + "#" + method_name)
                else:
                    error = test_case.findall('error')
                    if len(error) > 0:
                        error_tests_count += 1
                        failure_list['failure_name'] = error[0].attrib['type']
                        if 'message' in error[0].attrib:
                            failure_list['detail'] = error[0].attrib['message']
                        failure_list['is_error'] = True
                        failures.append(failure_list)
                        failingTestCases.add(class_name + "#" + method_name)
                    else:
                        skipTags = test_case.findall("skipped")
                        if len(skipTags) > 0:
                            skipping_tests_count += 1
                            skippingTestCases.add(class_name + '#' + method_name)
                        else:
                            passing_tests_count += 1
                            passingTestCases.add(class_name + '#' + method_name)

    return failingTestCases, passingTestCases


class JavaTestHandler(CommandHandler):
    class Meta:
        label = "java_test"

    def test_maven(self, context: Context, test: Test, env: dict = None) -> Tuple[CommandData, TestOutcome]:
        # clean the old test results at first
        _read_test_results(context.root.resolve() / context.project.name)
        failing_module = context.project.modules['failing_module']
        test_name = test.file
        additional_args = "-Dhttps.protocols=TLSv1.2 -Denforcer.skip=true -Dcheckstyle.skip=true " \
                          "-Dcobertura.skip=true -DskipITs=true -Drat.skip=true -Dlicense.skip=true -Dpmd.skip=true " \
                          "-Dfindbugs.skip=true -Dgpg.skip=true -Dskip.npm=true -Dskip.gulp=true -Dskip.bower=true " \
                          "-V -B"

        test_cmd = f"mvn test -Dtest={test_name} {additional_args}" if failing_module == "root" \
            else f"mvn test -P{failing_module} -Dtest={test_name} {additional_args}"

        cmd_data = CommandData(args=test_cmd, cwd=str(context.root.resolve() / context.project.name), env=env)
        super().__call__(cmd_data=cmd_data, msg=f"Testing {context.project.name}\n", raise_err=True)

        failed_tests, passed_tests = _read_test_results(context.root.resolve() / context.project.name)
        for failed_test in failed_tests:
            if failed_test == test_name:
                outcome = TestOutcome(instance_id=context.instance.id, co_id=context.instance.pointer, name=test.id,
                                      duration=round(cmd_data.duration, 3), exit_status=cmd_data.return_code,
                                      error=cmd_data.error, passed=False)
                return cmd_data, outcome

        for passed_test in passed_tests:
            if passed_test == test_name:
                outcome = TestOutcome(instance_id=context.instance.id, co_id=context.instance.pointer, name=test.id,
                                      duration=round(cmd_data.duration, 3), exit_status=cmd_data.return_code,
                                      error=cmd_data.error, passed=True)
                return cmd_data, outcome

        return cmd_data, TestOutcome(instance_id=context.instance.id, co_id=context.instance.pointer, name=test.id,
                                     duration=round(cmd_data.duration, 3), exit_status=cmd_data.return_code,
                                     error="Test not found", passed=True)

    def test_gradle(self, context: Context, test: Test, env: dict = None) -> Tuple[CommandData, TestOutcome]:
        # clean the old test results at first
        _read_test_results(context.root.resolve() / context.project.name)

        cmd_data = CommandData(args=f"./gradlew test", cwd=str(context.root.resolve() / context.project.name), env=env)
        super().__call__(cmd_data=cmd_data, msg=f"Testing {context.project.name}\n", raise_err=True)

        test_name = test.file
        failed_tests, passed_tests = _read_test_results(context.root.resolve() / context.project.name)
        for failed_test in failed_tests:
            if failed_test == test_name:
                outcome = TestOutcome(instance_id=context.instance.id, co_id=context.instance.pointer, name=test.id,
                                      duration=round(cmd_data.duration, 3), exit_status=cmd_data.return_code,
                                      error=cmd_data.error, passed=False)
                return cmd_data, outcome

        for passed_test in passed_tests:
            if passed_test == test_name:
                outcome = TestOutcome(instance_id=context.instance.id, co_id=context.instance.pointer, name=test.id,
                                      duration=round(cmd_data.duration, 3), exit_status=cmd_data.return_code,
                                      error=cmd_data.error, passed=True)
                return cmd_data, outcome

        return cmd_data, TestOutcome(instance_id=context.instance.id, co_id=context.instance.pointer, name=test.id,
                                     duration=round(cmd_data.duration, 3), exit_status=cmd_data.return_code,
                                     error="Test not found", passed=True)

    def save_outcome(self, cmd_data: CommandData, context: Context, tag: str = None):
        pass
