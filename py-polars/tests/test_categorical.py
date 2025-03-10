from __future__ import annotations

import io

import pytest

import polars as pl


def test_categorical_outer_join() -> None:
    with pl.StringCache():
        df1 = pl.DataFrame(
            [
                pl.Series("key1", [42]),
                pl.Series("key2", ["bar"], dtype=pl.Categorical),
                pl.Series("val1", [1]),
            ]
        ).lazy()

        df2 = pl.DataFrame(
            [
                pl.Series("key1", [42]),
                pl.Series("key2", ["bar"], dtype=pl.Categorical),
                pl.Series("val2", [2]),
            ]
        ).lazy()

    out = df1.join(df2, on=["key1", "key2"], how="outer").collect()
    expected = pl.DataFrame({"key1": [42], "key2": ["bar"], "val1": [1], "val2": [2]})

    assert out.frame_equal(expected)
    with pl.StringCache():
        dfa = pl.DataFrame(
            [
                pl.Series("key", ["foo", "bar"], dtype=pl.Categorical),
                pl.Series("val1", [3, 1]),
            ]
        )
        dfb = pl.DataFrame(
            [
                pl.Series("key", ["bar", "baz"], dtype=pl.Categorical),
                pl.Series("val2", [6, 8]),
            ]
        )

    df = dfa.join(dfb, on="key", how="outer")
    # the cast is important to test the rev map
    assert df["key"].cast(pl.Utf8).to_list() == ["bar", "baz", "foo"]


def test_read_csv_categorical() -> None:
    f = io.BytesIO()
    f.write(b"col1,col2,col3,col4,col5,col6\n'foo',2,3,4,5,6\n'bar',8,9,10,11,12")
    f.seek(0)
    df = pl.read_csv(f, has_header=True, dtypes={"col1": pl.Categorical})
    assert df["col1"].dtype == pl.Categorical


def test_categorical_lexical_sort() -> None:
    df = pl.DataFrame(
        {"cats": ["z", "z", "k", "a", "b"], "vals": [3, 1, 2, 2, 3]}
    ).with_columns(
        [
            pl.col("cats").cast(pl.Categorical).cat.set_ordering("lexical"),
        ]
    )

    out = df.sort(["cats"])
    assert out["cats"].dtype == pl.Categorical
    expected = pl.DataFrame(
        {"cats": ["a", "b", "k", "z", "z"], "vals": [2, 3, 2, 3, 1]}
    )
    assert out.with_column(pl.col("cats").cast(pl.Utf8)).frame_equal(expected)
    out = df.sort(["cats", "vals"])
    expected = pl.DataFrame(
        {"cats": ["a", "b", "k", "z", "z"], "vals": [2, 3, 2, 1, 3]}
    )
    assert out.with_column(pl.col("cats").cast(pl.Utf8)).frame_equal(expected)
    out = df.sort(["vals", "cats"])

    expected = pl.DataFrame(
        {"cats": ["z", "a", "k", "b", "z"], "vals": [1, 2, 2, 3, 3]}
    )
    assert out.with_column(pl.col("cats").cast(pl.Utf8)).frame_equal(expected)


def test_categorical_lexical_ordering_after_concat() -> None:
    with pl.StringCache():
        ldf1 = (
            pl.DataFrame([pl.Series("key1", [8, 5]), pl.Series("key2", ["fox", "baz"])])
            .lazy()
            .with_column(
                pl.col("key2").cast(pl.Categorical).cat.set_ordering("lexical")
            )
        )
        ldf2 = (
            pl.DataFrame(
                [pl.Series("key1", [6, 8, 6]), pl.Series("key2", ["fox", "foo", "bar"])]
            )
            .lazy()
            .with_column(
                pl.col("key2").cast(pl.Categorical).cat.set_ordering("lexical")
            )
        )
        df = (
            pl.concat([ldf1, ldf2])
            .with_column(pl.col("key2").cat.set_ordering("lexical"))
            .collect()
        )

        df.sort(["key1", "key2"])


def test_cat_to_dummies() -> None:
    df = pl.DataFrame({"foo": [1, 2, 3, 4], "bar": ["a", "b", "a", "c"]})
    df = df.with_column(pl.col("bar").cast(pl.Categorical))
    assert pl.get_dummies(df).to_dict(False) == {
        "foo_1": [1, 0, 0, 0],
        "foo_2": [0, 1, 0, 0],
        "foo_3": [0, 0, 1, 0],
        "foo_4": [0, 0, 0, 1],
        "bar_a": [1, 0, 1, 0],
        "bar_b": [0, 1, 0, 0],
        "bar_c": [0, 0, 0, 1],
    }


def test_comp_categorical_lit_dtype() -> None:
    df = pl.DataFrame(
        data={"column": ["a", "b", "e"], "values": [1, 5, 9]},
        columns=[("column", pl.Categorical), ("more", pl.Int32)],
    )

    assert df.with_column(
        pl.when(pl.col("column") == "e")
        .then("d")
        .otherwise(pl.col("column"))
        .alias("column")
    ).dtypes == [pl.Categorical, pl.Int32]


def test_categorical_describe_3487() -> None:
    # test if we don't err
    df = pl.DataFrame({"cats": ["a", "b"]})
    df = df.with_column(pl.col("cats").cast(pl.Categorical))
    df.describe()


def test_categorical_is_in_list() -> None:
    # this requires type coercion to cast.
    # we should not cast within the function as this would be expensive within a groupby
    # context that would be a cast per group
    with pl.StringCache():
        df = pl.DataFrame(
            {"a": [1, 2, 3, 1, 2], "b": ["a", "b", "c", "d", "e"]}
        ).with_column(pl.col("b").cast(pl.Categorical))

        cat_list = ["a", "b", "c"]
        assert df.filter(pl.col("b").is_in(cat_list)).to_dict(False) == {
            "a": [1, 2, 3],
            "b": ["a", "b", "c"],
        }


def test_unset_sorted_on_append() -> None:
    df1 = pl.DataFrame(
        [
            pl.Series("key", ["a", "b", "a", "b"], dtype=pl.Categorical),
            pl.Series("val", [1, 2, 3, 4]),
        ]
    ).sort("key")
    df2 = pl.DataFrame(
        [
            pl.Series("key", ["a", "b", "a", "b"], dtype=pl.Categorical),
            pl.Series("val", [5, 6, 7, 8]),
        ]
    ).sort("key")
    df = pl.concat([df1, df2], rechunk=False)
    assert df.groupby("key").count()["count"].to_list() == [4, 4]


def test_categorical_error_on_local_cmp() -> None:
    df_cat = pl.DataFrame(
        [
            pl.Series("a_cat", ["c", "a", "b", "c", "b"], dtype=pl.Categorical),
            pl.Series("b_cat", ["F", "G", "E", "G", "G"], dtype=pl.Categorical),
        ]
    )
    with pytest.raises(
        pl.ComputeError,
        match=(
            "Cannot compare categoricals originating from different sources. Consider"
            " setting a global string cache."
        ),
    ):
        df_cat.filter(pl.col("a_cat") == pl.col("b_cat"))


def test_cast_null_to_categorical() -> None:
    assert pl.DataFrame().with_columns(
        [pl.lit(None).cast(pl.Categorical).alias("nullable_enum")]
    ).dtypes == [pl.Categorical]
