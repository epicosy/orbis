from orbis.data.misc import Context
from orbis.data.results import CommandData
from orbis.handlers.command import CommandHandler


class JavaBuildHandler(CommandHandler):
    class Meta:
        label = "java_build"

    def build_maven(self, context: Context, env: dict = None) -> CommandData:
        additional_args = "-DskipTests -Dhttps.protocols=TLSv1.2 -Denforcer.skip=true -Dcheckstyle.skip=true " \
                          "-Dcobertura.skip=true -DskipITs=true -Drat.skip=true -Dlicense.skip=true -Dpmd.skip=true " \
                          "-Dfindbugs.skip=true -Dgpg.skip=true -Dskip.npm=true -Dskip.gulp=true -Dskip.bower=true " \
                          "-V -B"
        cmd_data = CommandData(args=f"mvn install {additional_args}", cwd=str(context.root.resolve() / context.project.name), env=env)
        super().__call__(cmd_data=cmd_data, msg=f"Building {context.project.name}\n", raise_err=True)
        return cmd_data

    def build_gradle(self, context: Context, env: dict = None) -> CommandData:
        cmd_data = CommandData(args=f"./gradlew compileTestJava", cwd=str(context.root.resolve() / context.project.name), env=env)
        super().__call__(cmd_data=cmd_data, msg=f"Building {context.project.name}\n", raise_err=True)
        return cmd_data

    def save_outcome(self, cmd_data: CommandData, context: Context, tag: str = None):
        pass