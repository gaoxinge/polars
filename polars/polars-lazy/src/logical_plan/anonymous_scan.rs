use crate::prelude::AnonymousScanOptions;
use polars_core::prelude::*;
use std::fmt::{Debug, Formatter};

pub trait AnonymousScan: Send + Sync {
    /// Creates a dataframe from the supplied function & scan options.
    fn scan(&self, scan_opts: AnonymousScanOptions) -> Result<DataFrame>;

    /// function to supply the schema.
    /// Allows for an optional infer schema argument for data sources with dynamic schemas
    fn schema(&self, _infer_schema_length: Option<usize>) -> Result<Schema> {
        Err(PolarsError::ComputeError(
            "Must supply either a schema or a schema function".into(),
        ))
    }
    /// specify if the scan provider should allow predicate pushdowns
    ///
    /// Defaults to `false`
    fn allows_predicate_pushdown(&self) -> bool {
        false
    }
    /// specify if the scan provider should allow projection pushdowns
    ///
    /// Defaults to `false`
    fn allows_projection_pushdown(&self) -> bool {
        false
    }
    /// specify if the scan provider should allow slice pushdowns
    ///
    /// Defaults to `false`
    fn allows_slice_pushdown(&self) -> bool {
        false
    }
}

impl<F> AnonymousScan for F
where
    F: Fn(AnonymousScanOptions) -> Result<DataFrame> + Send + Sync,
{
    fn scan(&self, scan_opts: AnonymousScanOptions) -> Result<DataFrame> {
        self(scan_opts)
    }
}

impl Debug for dyn AnonymousScan {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "anonymous_scan")
    }
}
