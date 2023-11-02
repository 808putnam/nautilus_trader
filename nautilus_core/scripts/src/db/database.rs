// -------------------------------------------------------------------------------------------------
//  Copyright (C) 2015-2023 Nautech Systems Pty Ltd. All rights reserved.
//  https://nautechsystems.io
//
//  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
//  You may not use this file except in compliance with the License.
//  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
//
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.
// -------------------------------------------------------------------------------------------------

use crate::utils::env::get_env_or;

#[derive(Debug)]
pub enum DbEngine{
    POSTGRES
}

pub fn get_connection_string(
    engine: DbEngine,
)-> String{
    let host = get_env_or("DB_HOST", "localhost");
    let port = get_env_or("DB_PORT", "5432");
    let user = get_env_or("DB_USER", "postgres");
    let password = get_env_or("DB_PASSWORD", "pass");
    let name = get_env_or("DB_NAME", "postgres");
    match engine { DbEngine::POSTGRES => {
        format!("postgres://{}:{}@{}:{}/{}", user, password, host, port, name)
    } }
}
