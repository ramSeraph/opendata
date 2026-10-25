# Publishing lgd-query releases

The repository workflow is `.github/workflows/lgd-query-publish.yml`, matching
the PyPI trusted-publisher configuration. It uses the `pypi` GitHub environment
and [OIDC trusted publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/).

A pushed `lgd-query-v<version>` tag builds this directory, checks that the tag
matches `pyproject.toml`, validates the distribution contents and PyPI metadata,
and tests the built wheel on Python 3.11 and 3.14. Only after these checks pass
does it upload the same wheel/source archive to PyPI and create a corresponding
GitHub release with those files attached. No scraper or history files are bundled.

For example, after committing version `0.2.0`:

```sh
git tag lgd-query-v0.2.0
git push origin lgd-query-v0.2.0
```

Manual workflow runs on a branch only build/test. A manual run on a matching
version tag also publishes. Failed publication jobs can be retried using the
same built artifacts. GitHub release titles and tags use the library prefix to
keep package versions separate from the data releases.

Before a retry uploads files, the workflow compares any existing PyPI files with
the checked local sizes and SHA-256 hashes. Different bytes under the same version
stop publication. Before creating/updating the GitHub release, it verifies that
both files match PyPI. If PyPI's metadata has not caught up yet, retry that job;
it will not attach unconfirmed files. For a partial upload, rerun failed jobs
with the original build artifacts instead of rebuilding the same version.
